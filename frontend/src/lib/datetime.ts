// `<input type="datetime-local">`은 사용자의 로컬 시간으로 해석되지만
// Date.toISOString()은 UTC를 반환한다. 그대로 min 속성에 넣으면 TZ만큼
// 어긋나서 "지금"인데도 과거로 표시되는 일이 생긴다.
export function nowLocalInput(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}
