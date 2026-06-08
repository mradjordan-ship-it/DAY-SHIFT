import { useNav } from "../App";

export default function OfflineScreen() {
  const { navigate } = useNav();

  return (
    <div className="h-full flex flex-col items-center justify-center px-6 text-center bg-background">
      <div className="w-20 h-20 rounded-full bg-amber-500/10 flex items-center justify-center mb-6">
        <svg className="w-10 h-10 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636a9 9 0 010 12.728m-3.536-3.536a4 4 0 010-5.656m-7.072 9.192a9 9 0 010-12.728m3.536 3.536a4 4 0 010 5.656" />
        </svg>
      </div>
      <h1 className="text-2xl font-bold text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>
        You're Offline
      </h1>
      <p className="text-sm text-muted-foreground max-w-xs leading-relaxed mb-6">
        It looks like you've lost your connection. Check your internet and try again.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-6 py-2.5 rounded-xl bg-amber-500 text-black text-sm font-semibold hover:bg-amber-400 transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}
