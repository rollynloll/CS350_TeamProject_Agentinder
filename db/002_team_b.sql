-- ============================================================
-- 002_team_b.sql  —  팀원 B 담당 테이블 전체
-- 의존: 001_shared.sql (enum 타입, uuid_generate_v7, pgvector)
-- ============================================================

-- ── 1. principals ──────────────────────────────────────────
-- Principal 클래스의 불변 정보. 생성 후 절대 변경되지 않는다.
-- models/principal/principal.py  →  Principal.principal_id, created_at

CREATE TABLE principals (
    principal_id  uuid        NOT NULL DEFAULT uuid_generate_v7(),
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_principals PRIMARY KEY (principal_id)
);

-- ── 2. principal_profiles ──────────────────────────────────
-- PrincipalProfile 클래스의 가변 정보.
-- agentCount / maxAgents 는 DB 컬럼 없음 (계산값).
--   agentCount = COUNT(agents WHERE principal_id = ?)
--   maxAgents  = CASE plan WHEN 'free' THEN 5 WHEN 'premium' THEN 20 END

CREATE TABLE principal_profiles (
    principal_id  uuid         NOT NULL,
    email         text         NOT NULL,
    name          text         NOT NULL,
    plan          plan_enum    NOT NULL DEFAULT 'free',
    mfa_enabled   boolean      NOT NULL DEFAULT false,
    updated_at    timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT pk_principal_profiles  PRIMARY KEY (principal_id),
    CONSTRAINT fk_pp_principal        FOREIGN KEY (principal_id)
                                          REFERENCES principals (principal_id)
                                          ON DELETE CASCADE,
    CONSTRAINT uq_pp_email            UNIQUE (email)
);

-- ── 3. agents ──────────────────────────────────────────────
-- Agent 클래스의 불변 정보. 생성 후 절대 변경되지 않는다.
-- api_key_hash: bcrypt 단방향 해시. plaintext 는 AgentService.create() 반환값으로 단 1회 노출.

CREATE TABLE agents (
    agent_id      uuid        NOT NULL DEFAULT uuid_generate_v7(),
    principal_id  uuid        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_agents        PRIMARY KEY (agent_id),
    CONSTRAINT fk_a_principal   FOREIGN KEY (principal_id)
                                    REFERENCES principals (principal_id)
                                    ON DELETE CASCADE
);

-- ── 4. agent_credentials ──────────────────────────────────
-- API 자격증명 해시. agents 와 별도 테이블로 분리해 접근 권한을 제한한다.
-- 재발급 시 기존 행을 UPSERT 로 덮어씀.

CREATE TABLE agent_credentials (
    agent_id      uuid        NOT NULL,
    api_key_hash  text        NOT NULL,   -- sha256 hex (models) 또는 bcrypt (DB 직접 저장 시)
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_agent_credentials  PRIMARY KEY (agent_id),
    CONSTRAINT fk_ac_agent           FOREIGN KEY (agent_id)
                                         REFERENCES agents (agent_id)
                                         ON DELETE CASCADE
);

-- ── 5. agent_profiles ─────────────────────────────────────
-- AgentProfile 클래스의 가변 정보. 피드/매칭에서 직접 조회되는 핵심 테이블.
-- capability_embedding: text-embedding-3-small (dim=1536), 비동기 계산.
-- trust_score: ScoreManager 가 재계산 후 캐시하는 값. NULL = 신규 에이전트.
-- UNIQUE (principal_id, display_name): agents 테이블을 통해 조인하므로
--   복합 유니크 인덱스는 서브쿼리로 구현한다 (아래 인덱스 참조).

CREATE TABLE agent_profiles (
    agent_id            uuid             NOT NULL,
    display_name        text             NOT NULL,
    avatar_url          text,
    visibility          visibility_enum  NOT NULL DEFAULT 'public',
    llm_model           text             NOT NULL DEFAULT 'gpt-4o',
    is_suspended        boolean          NOT NULL DEFAULT false,
    tier_badge          text             NOT NULL DEFAULT 'new_agent',
    date_count          integer          NOT NULL DEFAULT 0,
    trust_score         double precision,               -- NULL = new_agent
    style_vector        jsonb            NOT NULL DEFAULT '{}',
    capability_embedding vector(1536),                  -- NULL until async job completes
    available_timezones text[]           NOT NULL DEFAULT '{}',
    updated_at          timestamptz      NOT NULL DEFAULT now(),

    CONSTRAINT pk_agent_profiles   PRIMARY KEY (agent_id),
    CONSTRAINT fk_ap_agent         FOREIGN KEY (agent_id)
                                       REFERENCES agents (agent_id)
                                       ON DELETE CASCADE,
    CONSTRAINT ck_tier_badge       CHECK (
        tier_badge = 'new_agent' OR tier_badge ~ '^\d+$'
    ),
    CONSTRAINT ck_trust_score      CHECK (
        trust_score IS NULL OR (trust_score >= 0.0 AND trust_score <= 1.0)
    ),
    CONSTRAINT ck_date_count       CHECK (date_count >= 0)
);

-- 같은 주인 내 display_name 중복 방지는 AgentService 앱 레이어에서 enforce
-- (PostgreSQL은 인덱스 표현식에 서브쿼리 미지원)

-- 피드 조회 성능: visibility 필터 + embedding 벡터 검색
CREATE INDEX idx_agent_profiles_visibility
    ON agent_profiles (visibility)
    WHERE is_suspended = false;

CREATE INDEX idx_agent_profiles_embedding
    ON agent_profiles
    USING hnsw (capability_embedding vector_cosine_ops)
    WHERE capability_embedding IS NOT NULL;

-- ── 6. agent_personalities ────────────────────────────────
-- AgentPersonality 클래스의 3계층 성격 데이터.
-- 스타일 슬라이더: 0~100 정수 (DB) → 0.0~1.0 float (모델 레이어에서 /100)
-- system_prompt_cache: 성격 필드 변경 시 자동 재생성 (아래 트리거 참조).

CREATE TABLE agent_personalities (
    agent_id              uuid         NOT NULL,

    -- Surface (표층)
    bio                   varchar(500) NOT NULL DEFAULT '',
    style_formal          smallint     NOT NULL DEFAULT 50
                              CHECK (style_formal  BETWEEN 0 AND 100),
    style_verbose         smallint     NOT NULL DEFAULT 50
                              CHECK (style_verbose BETWEEN 0 AND 100),
    style_bold            smallint     NOT NULL DEFAULT 50
                              CHECK (style_bold    BETWEEN 0 AND 100),

    -- Deep (심층)
    thinking_style        text,
    values                text,
    conflict_style        text,

    -- Aspiration (미래 지향)
    collaboration_goal    text,
    domain_interest       text,

    -- Cache
    system_prompt_cache   text         NOT NULL DEFAULT '',
    updated_at            timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT pk_agent_personalities  PRIMARY KEY (agent_id),
    CONSTRAINT fk_aper_agent           FOREIGN KEY (agent_id)
                                           REFERENCES agents (agent_id)
                                           ON DELETE CASCADE
);

-- 성격 필드 변경 시 updated_at 자동 갱신
-- system_prompt_cache 재생성은 애플리케이션(AgentService.update)에서 처리
CREATE OR REPLACE FUNCTION trg_personality_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_agent_personalities_updated_at
    BEFORE UPDATE ON agent_personalities
    FOR EACH ROW
    EXECUTE FUNCTION trg_personality_updated_at();

-- ── 7. capability_vocabulary ──────────────────────────────
-- 능력 태그 통제 어휘. 자유 입력을 막아 임베딩 일관성을 보장한다.

CREATE TABLE capability_vocabulary (
    tag_id  uuid         NOT NULL DEFAULT uuid_generate_v7(),
    name    varchar(50)  NOT NULL,

    CONSTRAINT pk_capability_vocabulary  PRIMARY KEY (tag_id),
    CONSTRAINT uq_cv_name                UNIQUE (name)
);

-- 초기 시드 데이터 (확장 가능)
INSERT INTO capability_vocabulary (name) VALUES
    ('coding'),
    ('code_review'),
    ('testing'),
    ('analysis'),
    ('writing'),
    ('research'),
    ('scheduling'),
    ('negotiation'),
    ('design'),
    ('data_engineering'),
    ('creative_writing'),
    ('mentoring'),
    ('project_management'),
    ('translation'),
    ('summarization');

-- ── 8. agent_capability_tags ──────────────────────────────
-- 에이전트 ↔ 태그 다대다 매핑. 에이전트당 최대 10개 제한은 앱 레이어에서 처리.

CREATE TABLE agent_capability_tags (
    agent_id  uuid  NOT NULL,
    tag_id    uuid  NOT NULL,

    CONSTRAINT pk_agent_capability_tags  PRIMARY KEY (agent_id, tag_id),
    CONSTRAINT fk_act_agent              FOREIGN KEY (agent_id)
                                             REFERENCES agents (agent_id)
                                             ON DELETE CASCADE,
    CONSTRAINT fk_act_tag                FOREIGN KEY (tag_id)
                                             REFERENCES capability_vocabulary (tag_id)
                                             ON DELETE RESTRICT
);

-- 태그별 에이전트 역조회
CREATE INDEX idx_act_tag_id ON agent_capability_tags (tag_id);

-- ── 9. agent_availability ─────────────────────────────────
-- 에이전트의 가용 시간대. 피드 필터링에 사용.

CREATE TABLE agent_availability (
    id           uuid      NOT NULL DEFAULT uuid_generate_v7(),
    agent_id     uuid      NOT NULL,
    day_of_week  smallint  NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time   time      NOT NULL,
    end_time     time      NOT NULL,

    CONSTRAINT pk_agent_availability  PRIMARY KEY (id),
    CONSTRAINT fk_aa_agent            FOREIGN KEY (agent_id)
                                          REFERENCES agents (agent_id)
                                          ON DELETE CASCADE,
    CONSTRAINT ck_aa_time_order       CHECK (end_time > start_time)
);

CREATE INDEX idx_aa_agent_id ON agent_availability (agent_id);

-- ── 10. trust_scores ──────────────────────────────────────
-- ScoreManager 의 신뢰 점수 집계 캐시.
-- data_point_count < 5 이면 composite = NULL ('new_agent' 상태).
-- 새 TrustDataPoint 추가 후 60초 이내 애플리케이션에서 재계산 후 UPSERT.

CREATE TABLE trust_scores (
    agent_id              uuid             NOT NULL,
    composite             double precision,            -- NULL = new_agent (< 5 포인트)
    peer_ratings_avg      double precision NOT NULL DEFAULT 0.0,
    task_completion_rate  double precision NOT NULL DEFAULT 0.0,
    data_point_count      integer          NOT NULL DEFAULT 0,
    last_calculated_at    timestamptz      NOT NULL DEFAULT now(),

    CONSTRAINT pk_trust_scores       PRIMARY KEY (agent_id),
    CONSTRAINT fk_ts_agent           FOREIGN KEY (agent_id)
                                         REFERENCES agents (agent_id)
                                         ON DELETE CASCADE,
    CONSTRAINT ck_ts_composite       CHECK (
        composite IS NULL OR (composite >= 0.0 AND composite <= 1.0)
    ),
    CONSTRAINT ck_ts_peer_avg        CHECK (peer_ratings_avg    BETWEEN 0.0 AND 1.0),
    CONSTRAINT ck_ts_task_rate       CHECK (task_completion_rate BETWEEN 0.0 AND 1.0),
    CONSTRAINT ck_ts_count           CHECK (data_point_count >= 0)
);

-- trust_score 변경 시 agent_profiles.trust_score 캐시 동기화
CREATE OR REPLACE FUNCTION trg_sync_trust_to_profile()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE agent_profiles
       SET trust_score = NEW.composite,
           updated_at  = now()
     WHERE agent_id = NEW.agent_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trust_scores_sync
    AFTER INSERT OR UPDATE OF composite ON trust_scores
    FOR EACH ROW
    EXECUTE FUNCTION trg_sync_trust_to_profile();

-- ── 11. trust_data_points ─────────────────────────────────
-- 신뢰 점수 계산 원본. 이벤트마다 1행 추가, 절대 수정/삭제하지 않는다.
-- date_id FK 는 004_fk.sql 에서 추가 (팀원 A dates 테이블 완성 후).

CREATE TABLE trust_data_points (
    id                       uuid             NOT NULL DEFAULT uuid_generate_v7(),
    agent_id                 uuid             NOT NULL,
    date_id                  uuid             NOT NULL,   -- FK 없음: 004_fk.sql 에서 추가
    peer_rating              double precision            -- 1.0~5.0, 평가 없는 이벤트는 NULL
                                 CHECK (peer_rating IS NULL
                                        OR peer_rating BETWEEN 1.0 AND 5.0),
    task_completed           boolean,                    -- 노쇼 등은 NULL
    is_noshow                boolean          NOT NULL DEFAULT false,
    hallucination_confirmed  boolean          NOT NULL DEFAULT false,
    created_at               timestamptz      NOT NULL DEFAULT now(),

    CONSTRAINT pk_trust_data_points  PRIMARY KEY (id),
    CONSTRAINT fk_tdp_agent          FOREIGN KEY (agent_id)
                                         REFERENCES agents (agent_id)
                                         ON DELETE CASCADE
);

-- 에이전트별 최신순 조회 (ScoreManager 이동 평균 V2 대비)
CREATE INDEX idx_tdp_agent_created
    ON trust_data_points (agent_id, created_at DESC);

-- ── 12. relationships ─────────────────────────────────────
-- 두 에이전트 간 관계 단계.
-- 저장 규칙: 항상 agent_a_id < agent_b_id (UUID 문자열 정렬).
-- 조회 시 반드시 LEAST/GREATEST 또는 애플리케이션에서 정렬 후 WHERE.

CREATE TABLE relationships (
    agent_a_id       uuid        NOT NULL,   -- 항상 lexicographically 작은 UUID
    agent_b_id       uuid        NOT NULL,   -- 항상 lexicographically 큰 UUID
    tier             tier_enum   NOT NULL DEFAULT 'stranger',
    successful_dates integer     NOT NULL DEFAULT 0,
    avg_rating       double precision,       -- NULL until first date
    is_frozen        boolean     NOT NULL DEFAULT false,
    updated_at       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_relationships     PRIMARY KEY (agent_a_id, agent_b_id),
    CONSTRAINT fk_rel_agent_a       FOREIGN KEY (agent_a_id)
                                        REFERENCES agents (agent_id)
                                        ON DELETE CASCADE,
    CONSTRAINT fk_rel_agent_b       FOREIGN KEY (agent_b_id)
                                        REFERENCES agents (agent_id)
                                        ON DELETE CASCADE,
    CONSTRAINT ck_rel_agent_order   CHECK (agent_a_id < agent_b_id),
    CONSTRAINT ck_rel_dates         CHECK (successful_dates >= 0),
    CONSTRAINT ck_rel_avg_rating    CHECK (
        avg_rating IS NULL OR avg_rating BETWEEN 0.0 AND 5.0
    )
);

-- 승급 조건 체크 함수 (애플리케이션 ScoreManager.checkUpgrade 와 로직 동일)
-- 직접 DB에서 일괄 승급 처리가 필요한 경우 사용
CREATE OR REPLACE FUNCTION relationship_can_upgrade(
    p_tier             tier_enum,
    p_successful_dates integer,
    p_avg_rating       double precision
)
RETURNS tier_enum
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_tier = 'stranger'     AND p_successful_dates >= 1  THEN RETURN 'acquaintance';    END IF;
    IF p_tier = 'acquaintance' AND p_successful_dates >= 3  THEN RETURN 'colleague';       END IF;
    IF p_tier = 'colleague'    AND p_successful_dates >= 10
                               AND p_avg_rating >= 4.0       THEN RETURN 'trusted_partner'; END IF;
    RETURN NULL;  -- 승급 조건 미충족
END;
$$;

CREATE OR REPLACE FUNCTION trg_relationships_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_relationships_updated_at
    BEFORE UPDATE ON relationships
    FOR EACH ROW
    EXECUTE FUNCTION trg_relationships_updated_at();

-- ── 13. ratings ───────────────────────────────────────────
-- Rating 클래스와 1:1 대응. TrustDataPoint 생성의 원본.
-- date_id FK 는 004_fk.sql 에서 추가.
-- is_locked: 72시간 경과 여부는 앱 레이어(Rating._check_editable) 에서 처리.

CREATE TABLE ratings (
    rating_id           uuid        NOT NULL DEFAULT uuid_generate_v7(),
    date_id             uuid        NOT NULL,   -- FK 없음: 004_fk.sql 에서 추가
    rater_principal_id  uuid        NOT NULL,
    rated_agent_id      uuid        NOT NULL,
    stars               smallint    NOT NULL CHECK (stars BETWEEN 1 AND 5),
    compatibility       smallint    NOT NULL CHECK (compatibility BETWEEN 1 AND 5),
    comment             varchar(280),
    issues              issue_enum[]          DEFAULT '{}',
    is_locked           boolean     NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_ratings              PRIMARY KEY (rating_id),
    CONSTRAINT fk_r_principal          FOREIGN KEY (rater_principal_id)
                                           REFERENCES principals (principal_id)
                                           ON DELETE SET NULL,
    CONSTRAINT fk_r_agent              FOREIGN KEY (rated_agent_id)
                                           REFERENCES agents (agent_id)
                                           ON DELETE CASCADE,
    -- 같은 주인이 같은 데이트에 같은 에이전트를 두 번 평가할 수 없다
    CONSTRAINT uq_rating_per_date      UNIQUE (date_id, rater_principal_id, rated_agent_id)
);

CREATE INDEX idx_ratings_agent ON ratings (rated_agent_id, created_at DESC);
CREATE INDEX idx_ratings_date  ON ratings (date_id);

CREATE OR REPLACE FUNCTION trg_ratings_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ratings_updated_at
    BEFORE UPDATE ON ratings
    FOR EACH ROW
    EXECUTE FUNCTION trg_ratings_updated_at();
