-- ============================================================
-- 004_fk.sql  —  지연 FK 추가 (팀원 A dates 테이블 완성 후 적용)
-- 의존: 001_shared.sql, 002_team_b.sql, 003_team_a.sql
--
-- 팀원 A 와 합의 필요:
--   1. dates 테이블 이름 및 PK 컬럼명 확인
--   2. date_id 타입 UUID v7 통일 여부
--   3. 이 파일 적용 시점
-- ============================================================

-- trust_data_points.date_id → dates.date_id
ALTER TABLE trust_data_points
    ADD CONSTRAINT fk_tdp_date
        FOREIGN KEY (date_id)
        REFERENCES dates (date_id)   -- 팀원 A 테이블명/컬럼명 확정 후 수정
        ON DELETE SET NULL;          -- date 삭제 시 데이터 포인트는 유지

-- ratings.date_id → dates.date_id
ALTER TABLE ratings
    ADD CONSTRAINT fk_r_date
        FOREIGN KEY (date_id)
        REFERENCES dates (date_id)   -- 팀원 A 테이블명/컬럼명 확정 후 수정
        ON DELETE SET NULL;          -- date 삭제 시 평가 데이터는 보존
