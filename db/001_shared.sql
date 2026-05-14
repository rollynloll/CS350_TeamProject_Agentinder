-- ============================================================
-- 001_shared.sql  —  Enum 타입 + 확장 (팀 전체 합의 후 적용)
-- 팀원 A / B 모두 이 파일에 의존한다.
-- 이 파일을 수정할 때는 반드시 양 팀원과 사전 협의한다.
-- ============================================================

-- pgvector: capability_embedding 저장에 사용
CREATE EXTENSION IF NOT EXISTS vector;

-- UUID v7 생성 함수 (pg_uuidv7 확장 없이 순수 SQL 구현)
-- 팀원 A와 합의: 모든 PK에서 이 함수를 사용한다
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_bytes() 의존

CREATE OR REPLACE FUNCTION uuid_generate_v7()
RETURNS uuid
LANGUAGE plpgsql
PARALLEL SAFE
AS $$
DECLARE
  unix_ms  bigint;
  bytes    bytea;
  hex_str  text;
BEGIN
  unix_ms := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint;
  bytes   := gen_random_bytes(10);

  -- 48비트 타임스탬프 + ver(4비트=7) + rand_a(12비트) + var(2비트=10) + rand_b(62비트)
  hex_str :=
    lpad(to_hex(unix_ms), 12, '0') ||
    '7' ||
    lpad(to_hex(get_byte(bytes, 0) & 15), 1, '0') ||    -- rand_a (4비트)
    lpad(to_hex(get_byte(bytes, 1)), 2, '0') ||          -- rand_a (8비트)
    to_hex((get_byte(bytes, 2) & 63) | 128) ||           -- variant + rand_b start
    lpad(to_hex(get_byte(bytes, 3)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 4)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 5)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 6)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 7)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 8)), 2, '0') ||
    lpad(to_hex(get_byte(bytes, 9)), 2, '0');

  RETURN (
    substring(hex_str, 1,  8) || '-' ||
    substring(hex_str, 9,  4) || '-' ||
    substring(hex_str, 13, 4) || '-' ||
    substring(hex_str, 17, 4) || '-' ||
    substring(hex_str, 21, 12)
  )::uuid;
END;
$$;

-- ── Enum 타입 ──────────────────────────────────────────────
-- models/enums.py 와 1:1 대응. 값 추가 시 양 팀원 합의 필요.

CREATE TYPE plan_enum AS ENUM (
    'free',
    'premium'
);

CREATE TYPE visibility_enum AS ENUM (
    'public',
    'restricted',
    'hidden'
);

CREATE TYPE tier_enum AS ENUM (
    'stranger',
    'acquaintance',
    'colleague',
    'trusted_partner'
);

CREATE TYPE issue_enum AS ENUM (
    'hallucination',
    'latency',
    'unresponsive',
    'unauthorized'
);
