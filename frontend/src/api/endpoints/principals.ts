import { api } from "../client";

export type BePrincipal = {
  principal_id: string;
  email: string;
  name: string;
  plan: string; // 백엔드가 "FREE"/"PREMIUM" 대문자로 반환
  created_at: string | null;
};

/**
 * 로그인 직후 회원 레코드(principals + principal_profiles)를 보장한다.
 *
 * 백엔드 `POST /v1/principals`는 멱등이다(ON CONFLICT DO NOTHING 후 기존/신규 레코드 반환).
 * principal_id는 백엔드가 JWT의 `sub`에서 가져오므로 body는 선택이며,
 * email/name은 JWT 클레임이 우선하고 없을 때만 body 값을 사용한다.
 */
export async function ensurePrincipal(body?: {
  name?: string;
  email?: string;
}): Promise<BePrincipal> {
  return api.post<BePrincipal>("/principals", body ?? {});
}
