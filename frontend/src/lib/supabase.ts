import { createClient } from "@supabase/supabase-js";

// Supabase Auth 클라이언트 (OAuth 로그인 전용).
// anon key는 클라이언트 공개용 키다. PKCE 플로우로 GitHub 등 OAuth를 처리하고,
// 발급된 access_token(= 백엔드 SUPABASE_JWT_SECRET 으로 서명된 JWT)을 우리 백엔드가 검증한다.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!url || !anonKey) {
  console.warn(
    "VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY 가 설정되지 않았습니다. OAuth 로그인이 동작하지 않습니다.",
  );
}

export const supabase = createClient(url ?? "", anonKey ?? "", {
  auth: {
    flowType: "pkce",
    detectSessionInUrl: true,
    persistSession: true,
    autoRefreshToken: true,
  },
});
