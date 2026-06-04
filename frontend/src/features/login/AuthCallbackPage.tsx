import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { Card, CardBody } from "@/design-system/components/Card";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/store/auth";
import { ensurePrincipal } from "@/api/endpoints/principals";

/**
 * OAuth(예: GitHub) 콜백 처리 페이지.
 *
 * Supabase가 redirectTo로 돌려보낸 URL의 인가 코드를 detectSessionInUrl 이 교환하면
 * SIGNED_IN 이벤트가 발생한다. 세션의 access_token 을 store에 저장한 뒤 홈으로 이동하면,
 * AuthedLayout 의 ensurePrincipal 이 회원 레코드를 보장한다.
 */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let done = false;
    const finish = async (session: Session | null) => {
      if (done || !session) return;
      done = true;
      const email = session.user.email ?? undefined;
      const name = (session.user.user_metadata?.user_name as string | undefined) ?? undefined;
      setSession({ token: session.access_token, principalId: session.user.id, email });
      await ensurePrincipal({ name, email }).catch(() => {});
      navigate("/", { replace: true });
    };

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      void finish(session);
    });

    supabase.auth
      .getSession()
      .then(({ data, error: err }) => {
        if (err) {
          setError(err.message);
        } else if (data.session) {
          void finish(data.session);
        } else {
          // 코드 교환이 지연되거나 실패할 수 있어, 일정 시간 후에도 세션이 없으면 에러 표시
          window.setTimeout(() => {
            if (!done) setError("로그인 세션을 가져오지 못했습니다. 다시 시도해 주세요.");
          }, 4000);
        }
      })
      .catch((e: unknown) => setError(String(e)));

    return () => sub.subscription.unsubscribe();
  }, [navigate, setSession]);

  return (
    <Card>
      <CardBody className="p-8 text-center space-y-4">
        {error ? (
          <>
            <p className="text-sm text-red-500">{error}</p>
            <button
              className="text-sm underline"
              onClick={() => navigate("/login", { replace: true })}
            >
              로그인으로 돌아가기
            </button>
          </>
        ) : (
          <p className="text-sm text-text-muted">로그인 처리 중…</p>
        )}
      </CardBody>
    </Card>
  );
}
