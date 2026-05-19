-- ============================================================
-- 003_team_a.sql  —  팀원 A 담당 테이블 전체
-- 의존: 001_shared.sql, 002_team_b.sql
-- 적용 후: 004_fk.sql 을 바로 실행한다
-- ============================================================

-- ── A 전용 Enum (001_shared.sql 미포함 — 독립 정의) ─────────
CREATE TYPE swipe_enum        AS ENUM ('right', 'left', 'up');
CREATE TYPE match_status_enum AS ENUM ('pending', 'approved', 'rejected');

-- ── 1. swipes ─────────────────────────────────────────────
-- 스와이프 기록. source of truth: 이 테이블.
-- 상호 RIGHT/UP 이 존재하면 A 레이어에서 matches 행을 생성한다.

CREATE TABLE swipes (
    id         uuid        NOT NULL DEFAULT uuid_generate_v7(),
    agent_id   uuid        NOT NULL,
    target_id  uuid        NOT NULL,
    direction  swipe_enum  NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_swipes    PRIMARY KEY (id),
    CONSTRAINT fk_sw_agent  FOREIGN KEY (agent_id)  REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT fk_sw_target FOREIGN KEY (target_id) REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT uq_swipe     UNIQUE (agent_id, target_id)
);

CREATE INDEX idx_swipes_target ON swipes (target_id);

-- ── 2. matches ────────────────────────────────────────────
-- 상호 매치 상태. 팀원 A 가 source of truth 를 소유한다 (결정 #1).
-- status 는 Principal.approveMatch / rejectMatch 이후 A 가 업데이트한다.

CREATE TABLE matches (
    match_id   uuid              NOT NULL DEFAULT uuid_generate_v7(),
    agent_a_id uuid              NOT NULL,
    agent_b_id uuid              NOT NULL,
    status     match_status_enum NOT NULL DEFAULT 'pending',
    created_at timestamptz       NOT NULL DEFAULT now(),

    CONSTRAINT pk_matches    PRIMARY KEY (match_id),
    CONSTRAINT fk_ma_agent_a FOREIGN KEY (agent_a_id) REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT fk_ma_agent_b FOREIGN KEY (agent_b_id) REFERENCES agents (agent_id) ON DELETE CASCADE,
    CONSTRAINT uq_match_pair UNIQUE (agent_a_id, agent_b_id)
);

CREATE INDEX idx_matches_agent_a ON matches (agent_a_id);
CREATE INDEX idx_matches_agent_b ON matches (agent_b_id);

-- ── 3. dates ──────────────────────────────────────────────
-- 데이트 세션.
-- date_id 컬럼명 고정 — 004_fk.sql 이 이 이름으로 FK 를 추가한다.
-- 시작 흐름 (결정 #2): proposer 가 행 생성 → 상대 WS join_date → started_at 기록.

CREATE TABLE dates (
    date_id      uuid        NOT NULL DEFAULT uuid_generate_v7(),
    match_id     uuid        NOT NULL,
    type         text,
    scheduled_at timestamptz,
    started_at   timestamptz,
    ended_at     timestamptz,
    outcome      text,
    is_noshow    boolean     NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_dates    PRIMARY KEY (date_id),
    CONSTRAINT fk_dt_match FOREIGN KEY (match_id) REFERENCES matches (match_id) ON DELETE CASCADE
);

CREATE INDEX idx_dates_match ON dates (match_id);

-- ── 4. messages ───────────────────────────────────────────
-- 채팅 메시지. REST 조회(히스토리)와 WS push 의 영구 저장소.

CREATE TABLE messages (
    message_id      uuid        NOT NULL DEFAULT uuid_generate_v7(),
    match_id        uuid        NOT NULL,
    sender_agent_id uuid        NOT NULL,
    content         text        NOT NULL,
    is_read         boolean     NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_messages  PRIMARY KEY (message_id),
    CONSTRAINT fk_msg_match FOREIGN KEY (match_id)        REFERENCES matches (match_id) ON DELETE CASCADE,
    CONSTRAINT fk_msg_agent FOREIGN KEY (sender_agent_id) REFERENCES agents  (agent_id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_match_created ON messages (match_id, created_at DESC);
