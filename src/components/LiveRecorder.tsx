import { useState, useRef, useEffect } from "react";
import { Video, Circle, Square, RotateCcw, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface LiveRecorderProps {
  onRecorded: (blob: Blob, url: string) => void;
  onCancel: () => void;
  fullscreen?: boolean;
}

type RecorderState = "idle" | "previewing" | "recording" | "review";

export default function LiveRecorder({ onRecorded, onCancel, fullscreen }: LiveRecorderProps) {
  const [state, setState] = useState<RecorderState>("previewing");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");
  const [facingMode, setFacingMode] = useState<"user" | "environment">("environment");

  const liveRef = useRef<HTMLVideoElement>(null);
  const reviewRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const blobRef = useRef<Blob | null>(null);
  const previewUrlRef = useRef<string>("");

  // Start camera preview
  const startCamera = async (facing: "user" | "environment" = facingMode) => {
    setError("");
    try {
      // Stop any existing stream
      streamRef.current?.getTracks().forEach((t) => t.stop());

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: facing,
          width: { ideal: 1920, max: 3840 },
          height: { ideal: 1080, max: 2160 },
          frameRate: { ideal: 30, max: 60 },
        },
        audio: true,
      });
      streamRef.current = stream;

      if (liveRef.current) {
        liveRef.current.srcObject = stream;
        await liveRef.current.play().catch(() => {});
      }
      setState("previewing");
    } catch (e: unknown) {
      setError(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Camera access denied. Please allow camera permissions."
          : "Could not access camera. Try a different browser."
      );
    }
  };

  // Auto-start camera on mount
  useEffect(() => {
    let mounted = true;
    startCamera().then(() => {
      if (!mounted) {
        streamRef.current?.getTracks().forEach((t) => t.stop());
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const flipCamera = () => {
    const next = facingMode === "environment" ? "user" : "environment";
    setFacingMode(next);
    if (state === "previewing" || state === "recording") {
      startCamera(next);
    }
  };

  const startRecording = () => {
    if (!streamRef.current) return;
    chunksRef.current = [];

    // Pick best supported mime
    const mimeType = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]
      .find((m) => MediaRecorder.isTypeSupported(m)) ?? "";

    const recorderOptions: MediaRecorderOptions = {
      ...(mimeType ? { mimeType } : {}),
      videoBitsPerSecond: 8_000_000,   // 8 Mbps — high quality source for FFmpeg
      audioBitsPerSecond: 192_000,     // 192 kbps audio
    };
    const recorder = new MediaRecorder(streamRef.current, recorderOptions);
    recorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType || "video/webm" });
      blobRef.current = blob;
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      setState("review");
      if (reviewRef.current) {
        reviewRef.current.src = url;
        reviewRef.current.load();
      }
    };

    recorder.start(100); // collect chunks every 100ms
    setState("recording");
    setSeconds(0);

    timerRef.current = setInterval(() => {
      setSeconds((s) => {
        if (s >= 59) {
          stopRecording();
          return 60;
        }
        return s + 1;
      });
    }, 1000);
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
  };

  const retake = () => {
    blobRef.current = null;
    previewUrlRef.current = "";
    setSeconds(0);
    setState("idle");
  };

  const confirm = () => {
    if (blobRef.current && previewUrlRef.current) {
      onRecorded(blobRef.current, previewUrlRef.current);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className={cn("flex flex-col", fullscreen ? "h-full" : "gap-4")}>
      {/* Viewfinder */}
      <div className={cn("relative overflow-hidden bg-black", fullscreen ? "h-full" : "rounded-2xl aspect-video")}>
        {/* Live preview (hidden during review) */}
        <video
          ref={liveRef}
          className={`w-full h-full object-cover ${state === "review" ? "hidden" : ""}`}
          autoPlay
          playsInline
          muted
        />

        {/* Review playback */}
        {state === "review" && (
          <video
            ref={reviewRef}
            className="w-full h-full object-cover"
            controls
            playsInline
            src={previewUrlRef.current}
          />
        )}

        {/* Idle placeholder */}
        {state === "idle" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-secondary">
            <Video size={40} className="text-muted-foreground" />
            <p className="text-muted-foreground text-sm">Tap to start camera</p>
          </div>
        )}

        {/* Recording indicator */}
        {state === "recording" && (
          <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/50 backdrop-blur px-2.5 py-1 rounded-full">
            <span className="w-2 h-2 rounded-full bg-red-500 pulse-orange" />
            <span className="text-white text-xs font-semibold tabular-nums">{formatTime(seconds)}</span>
          </div>
        )}

        {/* Flip camera button */}
        {(state === "previewing" || state === "recording") && (
          <button
            onClick={flipCamera}
            className="absolute top-3 right-3 w-9 h-9 bg-black/40 backdrop-blur rounded-full flex items-center justify-center text-white"
          >
            <RotateCcw size={16} />
          </button>
        )}

        {/* Timer progress bar */}
        {state === "recording" && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
            <div
              className="h-full bg-red-500 transition-all duration-1000"
              style={{ width: `${(seconds / 60) * 100}%` }}
            />
          </div>
        )}

        {/* Overlay Controls for Previewing / Recording */}
        {(state === "previewing" || state === "recording") && (
          <>
            <div className="absolute bottom-4 right-4 z-10 flex items-center gap-3">
              {fullscreen && <span className="text-white/80 text-sm font-medium">Record Video</span>}
              {state === "previewing" ? (
                <button
                  onClick={startRecording}
                  className="w-12 h-12 rounded-full bg-red-500/90 border-[3px] border-white flex items-center justify-center ember-glow shadow-xl active:scale-95 transition-transform"
                >
                  <Circle size={18} className="text-white fill-white" />
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  className="w-12 h-12 rounded-full bg-red-500 border-[3px] border-white flex items-center justify-center shadow-xl active:scale-95 transition-transform"
                >
                  <Square size={14} className="text-white fill-white" />
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">
          {error}
        </div>
      )}

      {/* Controls */}
      {state === "idle" && (
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 rounded-xl border border-border text-muted-foreground text-sm font-medium"
          >
            Back
          </button>
          <button
            onClick={() => startCamera()}
            className="flex-1 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold ember-glow"
          >
            Open Camera
          </button>
        </div>
      )}





      {state === "review" && (
        <div className="space-y-2">
          <p className="text-center text-sm text-muted-foreground">Happy with the take?</p>
          <div className="flex gap-3">
            <button
              onClick={retake}
              className="flex-1 py-3 rounded-xl border border-border text-sm font-medium flex items-center justify-center gap-2"
            >
              <RotateCcw size={15} /> Retake
            </button>
            <button
              onClick={confirm}
              className="flex-1 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold ember-glow flex items-center justify-center gap-2"
            >
              <Check size={15} /> Use This
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
