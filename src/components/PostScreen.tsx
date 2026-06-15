import { useState, useRef, useEffect } from "react";
import { useAuth, useNav } from "../App";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CheckCircle, Upload, X, Image as ImageIcon, VideoIcon, Tag, Calendar, Sparkles, Lightbulb, Clock, Star, HardHat, Building2, Link, Loader2, Camera } from "lucide-react";
import { cn } from "@/lib/utils";
import LiveRecorder from "./LiveRecorder";

type Step = "create" | "record" | "done";

export default function PostScreen() {
  const { user, token } = useAuth();
  const { navigate, params: navParams } = useNav();
  const isAdmin = user?.is_admin ?? false;
  const [step, setStep] = useState<Step>("create");
  const [postType, setPostType] = useState<"worker" | "employer">(
    user?.role === "employer" ? "employer" : user?.role === "admin" ? "employer" : "worker"
  );
  const [showRecorder, setShowRecorder] = useState(false);

  // Recording state (non-admin)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState("");
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState("");

  // Admin upload state
  const [uploadedImageUrl, setUploadedImageUrl] = useState("");
  const [uploadedVideoUrlAdmin, setUploadedVideoUrlAdmin] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [videoPreviewAdmin, setVideoPreviewAdmin] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [videoUploading, setVideoUploading] = useState(false);
  const [imageProgress, setImageProgress] = useState(0);
  const [videoProgress, setVideoProgress] = useState(0);
  const [imageError, setImageError] = useState("");
  const [videoError, setVideoError] = useState("");
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "1:1" | "4:5" | "16:9">("9:16");

  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);

  // Default category based on role: crew → "crew", employer → "sale", admin → "general"
  const defaultCategory = isAdmin ? "general" : postType === "worker" ? "crew" : "sale";

  const [form, setForm] = useState({
    title: "",
    description: "",
    cuisine_type: "",
    pay_rate: "",
    hours: "",
    experience_level: "",
    location: "",
    category: defaultCategory,
    price: "",
    event_date: "",
    event_time: "",
    scheduled_at: "",
  });
  const [submitting, setSubmitting] = useState(false);

  // URL import state
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importSuccess, setImportSuccess] = useState(false);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
        <p className="text-muted-foreground">Sign in to post</p>
      </div>
    );
  }

  if (!user.email_verified) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-4">
        <div className="w-16 h-16 rounded-full bg-amber-500/15 flex items-center justify-center">
          <svg className="w-8 h-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
        </div>
        <h2 className="text-xl font-bold text-foreground">Verify Your Email</h2>
        <p className="text-muted-foreground text-sm max-w-xs">You need to verify your email before you can post. Check your inbox or request a new link.</p>
        <Button
          className="bg-primary text-primary-foreground hover:bg-primary/90 ember-glow"
          onClick={async () => {
            try {
              const res = await fetch("/api/auth/resend-verification", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: user.email }),
              });
              const data = await res.json();
              alert(data.message || "Check your email");
            } catch { alert("Failed to resend verification"); }
          }}
        >
          Resend Verification Email
        </Button>
      </div>
    );
  }

  // Upload helper with progress tracking via XHR
  const uploadWithProgress = (
    file: File,
    endpoint: string,
    onProgress: (pct: number) => void
  ): Promise<{ url: string }> => {
    return new Promise((resolve, reject) => {
      const fd = new FormData();
      fd.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", endpoint);
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new Error("Invalid response"));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || "Upload failed"));
          } catch {
            reject(new Error("Upload failed"));
          }
        }
      };
      xhr.onerror = () => reject(new Error("Network error"));
      xhr.send(fd);
    });
  };

  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  // Import job data from URL
  const handleImportUrl = async () => {
    if (!importUrl.trim()) return;
    setImporting(true);
    setImportError("");
    setImportSuccess(false);
    try {
      const res = await fetch("/api/import-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: importUrl.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setImportError(data.detail || "Could not import from that URL");
        return;
      }
      // Pre-fill form fields from imported data
      if (data.title) set("title", data.title);
      if (data.location) set("location", data.location);
      if (data.pay_rate) set("pay_rate", data.pay_rate);
      if (data.hours) set("hours", data.hours);
      if (data.experience_level) set("experience_level", data.experience_level);
      if (data.cuisine_type) set("cuisine_type", data.cuisine_type);
      if (data.category && data.category !== "general") set("category", data.category);
      // Build description with contact info
      let desc = data.description || "";
      if (data.contact_info && !desc.includes(data.contact_info)) {
        desc = desc ? `${desc}\n\n📞 ${data.contact_info}` : `📞 ${data.contact_info}`;
      }
      if (desc) set("description", desc);
      // If we got a video URL, use it directly
      if (data.video_url) {
        setUploadedVideoUrlAdmin(data.video_url);
        setVideoPreviewAdmin(data.video_url);
      }
      // If we got an image, use it
      if (data.image_url && !uploadedImageUrl) {
        setUploadedImageUrl(data.image_url);
        setImagePreview(data.image_url);
      }
      // Auto-set aspect ratio from imported image dimensions
      if (data.aspect_ratio) {
        setAspectRatio(data.aspect_ratio);
      }
      setImportSuccess(true);
      setImportUrl("");
      setTimeout(() => setImportSuccess(false), 3000);
    } catch {
      setImportError("Network error — please try again");
    } finally {
      setImporting(false);
    }
  };

  // Handle Web Share Target incoming data — read from nav params (set by App.tsx)
  useEffect(() => {
    const sharedUrl = (navParams.shared_url as string) || "";
    const sharedTitle = (navParams.title as string) || "";
    const sharedDesc = (navParams.description as string) || "";
    if (sharedUrl) {
      setImportUrl(sharedUrl);
    }
    if (sharedTitle) setForm((f) => ({ ...f, title: sharedTitle }));
    if (sharedDesc && sharedDesc !== sharedUrl) setForm((f) => ({ ...f, description: sharedDesc }));
  }, [navParams.shared_url, navParams.title, navParams.description]);

  // Admin upload handlers
  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageError("");
    setImagePreview(URL.createObjectURL(file));
    setImageUploading(true);
    setImageProgress(0);
    try {
      const data = await uploadWithProgress(file, "/api/upload/image", setImageProgress);
      setUploadedImageUrl(data.url);
    } catch (err) {
      setImageError(err instanceof Error ? err.message : "Upload failed");
      setImagePreview(null);
    } finally {
      setImageUploading(false);
    }
  };

  const handleVideoSelectAdmin = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setVideoError("");
    setVideoPreviewAdmin(URL.createObjectURL(file));
    setVideoUploading(true);
    setVideoProgress(0);
    try {
      const data = await uploadWithProgress(file, "/api/upload/video", setVideoProgress);
      setUploadedVideoUrlAdmin(data.url);
    } catch (err) {
      setVideoError(err instanceof Error ? err.message : "Upload failed");
      setVideoPreviewAdmin(null);
    } finally {
      setVideoUploading(false);
    }
  };

  const resetImage = () => {
    setUploadedImageUrl("");
    setImagePreview(null);
    setImageError("");
    if (imageInputRef.current) imageInputRef.current.value = "";
  };

  const resetVideo = () => {
    setUploadedVideoUrlAdmin("");
    setVideoPreviewAdmin(null);
    setVideoError("");
    if (videoInputRef.current) videoInputRef.current.value = "";
  };

  const resetAll = () => {
    setStep("create");
    setShowRecorder(false);
    setRecordedBlob(null);
    setRecordedUrl("");
    setUploadedVideoUrl("");
    resetImage();
    resetVideo();
    setAspectRatio("9:16");
    setForm({ title: "", description: "", cuisine_type: "", pay_rate: "", hours: "", experience_level: "", location: "", category: defaultCategory, price: "", event_date: "", event_time: "", scheduled_at: "" });
  };

  // Non-admin: recorded video
  const handleRecorded = async (blob: Blob, url: string) => {
    setRecordedBlob(blob);
    setRecordedUrl(url);
    setSubmitting(true);
    setVideoProgress(0);
    try {
      const file = new File([blob], `recording_${Date.now()}.webm`, { type: blob.type });
      const data = await uploadWithProgress(file, "/api/upload/video", setVideoProgress);
      setUploadedVideoUrl(data.url);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    doSubmit();
  };

  const doSubmit = async () => {
    setSubmitting(true);
    try {
      const fd = new FormData();
      const videoUrl = uploadedVideoUrlAdmin || uploadedVideoUrl || "";

      fd.append("type", postType);
      fd.append("post_type", videoUrl ? "video" : uploadedImageUrl ? "image" : "text");
      fd.append("category", form.category);
      fd.append("price", form.price);
      fd.append("event_date", form.event_date);
      fd.append("event_time", form.event_time);
      fd.append("scheduled_at", form.scheduled_at);
      fd.append("aspect_ratio", aspectRatio);
      fd.append("title", form.title);
      fd.append("description", form.description);
      fd.append("video_url", videoUrl);
      fd.append("image_url", uploadedImageUrl || "");

      // Extra metadata fields (all users can add these)
      if (!isAdmin) {
        fd.append("cuisine_type", form.cuisine_type);
        fd.append("pay_rate", form.pay_rate);
        fd.append("hours", form.hours);
        fd.append("experience_level", form.experience_level);
        fd.append("location", form.location);
      }

      const res = await fetch("/api/videos", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (res.ok) {
        const data = await res.json();
        // If sponsored post (non-admin), redirect to Boost for payment
        if (form.category === "sponsored" && !isAdmin && data.id) {
          navigate("boost", { videoId: data.id });
        } else {
          setStep("done");
        }
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(errorData.detail || "Failed to post. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Determine if post is valid — text-only posts just need a description
  const canPost = Boolean(
    form.description.trim() && !submitting
  );

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      {/* Progress bar */}
      <div className="h-1 bg-secondary">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{
            width: step === "create" ? "50%" : "100%",
          }}
        />
      </div>

      <div className="p-4">
        {/* Step: create — unified post form for all users */}
        {step === "create" && (
          <div className="space-y-3">
            <div className="flex items-baseline justify-between">
              <div>
                <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
                  Create a Post
                </h2>
                <p className="text-muted-foreground text-[11px]">
                  <span className="text-amber-500 font-semibold"><Lightbulb size={11} className="inline mr-0.5" />Add media for 3x more matches — or just post text!</span>
                </p>
              </div>
            </div>

            {/* Import from URL */}
            <div className="space-y-1.5 rounded-xl border border-border bg-secondary/30 p-3">
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                <Link size={10} /> Import from URL
                <span className="font-normal normal-case text-muted-foreground/60">— paste a link from Facebook, X, LinkedIn, Indeed, etc.</span>
              </Label>
              <div className="flex gap-2">
                <Input
                  value={importUrl}
                  onChange={(e) => { setImportUrl(e.target.value); setImportError(""); setImportSuccess(false); }}
                  placeholder="https://x.com/user/status/... or any job link"
                  className="bg-secondary border-border h-8 text-sm flex-1"
                  onKeyDown={(e) => { if (e.key === "Enter") handleImportUrl(); }}
                />
                <Button
                  type="button"
                  onClick={handleImportUrl}
                  disabled={importing || !importUrl.trim()}
                  size="sm"
                  className={cn("h-8 px-3 text-xs", importSuccess ? "bg-green-600 text-white" : "bg-primary text-primary-foreground")}
                >
                  {importing ? <Loader2 size={14} className="animate-spin" /> : importSuccess ? "✓ Done" : "Import"}
                </Button>
              </div>
              {importError && <p className="text-[11px] text-destructive">{importError}</p>}
              {importSuccess && <p className="text-[11px] text-green-500">Fields pre-filled — review and add media before posting</p>}
            </div>

            {/* Media Uploads + Layout */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                  Media & Layout
                  <span className="font-normal normal-case text-muted-foreground/60">(aspect ratio)</span>
                </Label>
                <div className="flex items-center gap-1">
                  <span className="text-[9px] text-muted-foreground mr-1">Tall</span>
                  {(["9:16", "4:5", "1:1", "16:9"] as const).map((r) => (
                    <button key={r} type="button" onClick={() => setAspectRatio(r)}
                      className={cn("px-2 py-0.5 rounded text-[9px] font-bold transition-all", aspectRatio === r ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                    >{r}</button>
                  ))}
                  <span className="text-[9px] text-muted-foreground ml-1">Wide</span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} className="hidden" />
                  <div className={cn("w-full rounded-xl overflow-hidden border transition-all duration-300", imagePreview ? "border-border bg-black" : "border-2 border-dashed border-border hover:border-primary/50 hover:bg-secondary/50 bg-secondary/20")}>
                    <div className="w-full flex items-center justify-center overflow-hidden" style={imagePreview ? { aspectRatio: aspectRatio === "9:16" ? "9/16" : aspectRatio === "4:5" ? "4/5" : aspectRatio === "1:1" ? "1/1" : "16/9" } : { height: '7rem' }}>
                      {imagePreview ? (
                        <div className="relative w-full h-full">
                          <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                          {!imageUploading && <button onClick={resetImage} className="absolute top-2 right-2 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/70 transition-colors"><X size={16} /></button>}
                        </div>
                      ) : (
                        <button onClick={() => imageInputRef.current?.click()} disabled={imageUploading} className="w-full h-28 flex flex-col items-center justify-center">
                          {imageUploading ? <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" /> : <><ImageIcon className="w-6 h-6 text-muted-foreground mb-1" /><span className="text-xs font-medium text-muted-foreground">📷 Image</span></>}
                        </button>
                      )}
                    </div>
                  </div>
                  {imageError && <p className="text-xs text-destructive mt-1">{imageError}</p>}
                  {imageUploading && (
                    <div className="mt-1 flex items-center gap-2">
                      <div className="flex-1 bg-secondary rounded-full h-1.5 overflow-hidden">
                        <div className="h-full bg-primary rounded-full transition-all duration-200" style={{ width: `${imageProgress}%` }} />
                      </div>
                      <span className="text-[10px] text-muted-foreground">{imageProgress}%</span>
                    </div>
                  )}
                </div>
                <div className="space-y-1">
                  <input ref={videoInputRef} type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" onChange={handleVideoSelectAdmin} className="hidden" />
                  <div className={cn("w-full rounded-xl overflow-hidden border transition-all duration-300", videoPreviewAdmin ? "border-border bg-black" : "border-2 border-dashed border-border hover:border-primary/50 hover:bg-secondary/50 bg-secondary/20")}>
                    <div className="w-full flex items-center justify-center overflow-hidden" style={videoPreviewAdmin ? { aspectRatio: aspectRatio === "9:16" ? "9/16" : aspectRatio === "4:5" ? "4/5" : aspectRatio === "1:1" ? "1/1" : "16/9" } : { height: '7rem' }}>
                      {videoPreviewAdmin ? (
                        <div className="relative w-full h-full">
                          <video src={videoPreviewAdmin} controls className="w-full h-full object-cover" />
                          {!videoUploading && <button onClick={resetVideo} className="absolute top-2 right-2 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/70 transition-colors"><X size={16} /></button>}
                        </div>
                      ) : (
                        <button onClick={() => videoInputRef.current?.click()} disabled={videoUploading} className="w-full h-28 flex flex-col items-center justify-center">
                          {videoUploading ? <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" /> : <><VideoIcon className="w-6 h-6 text-muted-foreground mb-1" /><span className="text-xs font-medium text-muted-foreground">🎬 Video</span></>}
                        </button>
                      )}
                    </div>
                  </div>
                  {videoError && <p className="text-xs text-destructive mt-1">{videoError}</p>}
                  {videoUploading && (
                    <div className="mt-1 flex items-center gap-2">
                      <div className="flex-1 bg-secondary rounded-full h-1.5 overflow-hidden">
                        <div className="h-full bg-primary rounded-full transition-all duration-200" style={{ width: `${videoProgress}%` }} />
                      </div>
                      <span className="text-[10px] text-muted-foreground">{videoProgress}%</span>
                    </div>
                  )}
                </div>
                {/* Camera record button */}
                <div className="space-y-1">
                  <div className={cn("w-full rounded-xl overflow-hidden border transition-all duration-300", showRecorder ? "border-primary bg-primary/10" : "border-2 border-dashed border-border hover:border-primary/50 hover:bg-secondary/50 bg-secondary/20")}>
                    <button
                      onClick={() => setShowRecorder(!showRecorder)}
                      disabled={submitting}
                      className="w-full h-28 flex flex-col items-center justify-center"
                    >
                      {recordedUrl ? (
                        <>
                          <CheckCircle className="w-6 h-6 text-green-500 mb-1" />
                          <span className="text-xs font-medium text-green-500">✓ Recorded</span>
                        </>
                      ) : (
                        <>
                          <Camera className="w-6 h-6 text-muted-foreground mb-1" />
                          <span className="text-xs font-medium text-muted-foreground">🎥 Camera</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Inline Camera Recorder */}
            {showRecorder && (
              <div className="space-y-2 rounded-xl border border-border bg-secondary/30 p-3">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                    <Camera size={10} /> Record Video
                  </Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-muted-foreground"
                    onClick={() => setShowRecorder(false)}
                  >
                    <X size={14} /> Close
                  </Button>
                </div>
                {submitting ? (
                  <div className="flex flex-col items-center justify-center py-8 gap-3">
                    <div className="w-full max-w-xs bg-secondary rounded-full h-2 overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-200"
                        style={{ width: `${videoProgress}%` }}
                      />
                    </div>
                    <p className="text-muted-foreground text-sm">Uploading… {videoProgress}%</p>
                  </div>
                ) : (
                  <LiveRecorder
                    onRecorded={(blob, url) => {
                      handleRecorded(blob, url);
                      setShowRecorder(false);
                    }}
                    onCancel={() => setShowRecorder(false)}
                  />
                )}
              </div>
            )}

            {/* Recorded video preview */}
            {recordedUrl && !showRecorder && (
              <div className="rounded-xl border border-border overflow-hidden">
                <div className="relative" style={{ aspectRatio: aspectRatio === "9:16" ? "9/16" : aspectRatio === "4:5" ? "4/5" : aspectRatio === "1:1" ? "1/1" : "16/9" }}>
                  <video src={recordedUrl} controls className="w-full h-full object-cover" />
                  <button
                    onClick={() => { setRecordedBlob(null); setRecordedUrl(""); setUploadedVideoUrl(""); }}
                    className="absolute top-2 right-2 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/70 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
                <p className="text-[10px] text-muted-foreground px-2 py-1 bg-secondary/30">✓ Recording uploaded</p>
              </div>
            )}

            {/* Description */}
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Description *</Label>
              <Textarea
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
                placeholder={postType === "worker" ? "Describe your skills, experience, and what you're looking for..." : "Describe the role, spot, and what you're looking for in a crew member..."}
                rows={2}
                className="bg-secondary border-border resize-none text-sm h-auto"
                required
              />
            </div>

            {/* Title */}
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Title</Label>
              <Input
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder={postType === "worker" ? "Experienced Line Cook — Available Now" : "Need Sous Chef for Friday Dinner Service"}
                className="bg-secondary border-border h-8 text-sm"
              />
            </div>

            {/* Post Category + Price + Event fields */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Category</Label>
                <Select onValueChange={(v) => set("category", v)} value={form.category}>
                  <SelectTrigger className="bg-secondary border-border h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {isAdmin && <SelectItem value="general"><Sparkles size={12} className="inline mr-1" /> General</SelectItem>}
                    {isAdmin && <SelectItem value="kitchen"><Building2 size={12} className="inline mr-1" /> Kitchen</SelectItem>}
                    {(postType === "worker" || isAdmin) && <SelectItem value="crew"><HardHat size={12} className="inline mr-1" /> Crew</SelectItem>}
                    <SelectItem value="sale"><Tag size={12} className="inline mr-1" /> For Sale</SelectItem>
                    <SelectItem value="event"><Calendar size={12} className="inline mr-1" /> Event</SelectItem>
                    <SelectItem value="sponsored"><Star size={12} className="inline mr-1 fill-primary text-primary" /> Sponsored</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {form.category === "sale" && (
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Price</Label>
                  <Input value={form.price} onChange={(e) => set("price", e.target.value)} placeholder="$150" className="bg-secondary border-border h-8 text-sm" />
                </div>
              )}
              {form.category === "event" && (
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Date</Label>
                  <Input type="date" value={form.event_date} onChange={(e) => set("event_date", e.target.value)} className="bg-secondary border-border h-8 text-sm" />
                </div>
              )}
            </div>
            {form.category === "event" && (
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Time</Label>
                  <Input type="time" value={form.event_time} onChange={(e) => set("event_time", e.target.value)} className="bg-secondary border-border h-8 text-sm" />
                </div>
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Price</Label>
                  <Input value={form.price} onChange={(e) => set("price", e.target.value)} placeholder="$25 or Free" className="bg-secondary border-border h-8 text-sm" />
                </div>
              </div>
            )}

            {/* Schedule Post */}
            {user && (
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1"><Clock size={10} /> Schedule Post</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-0.5">
                    <Input type="date" value={form.scheduled_at ? form.scheduled_at.split("T")[0] : ""} onChange={(e) => {
                      const time = form.scheduled_at ? form.scheduled_at.split("T")[1] || "T12:00" : "T12:00";
                      set("scheduled_at", e.target.value ? `${e.target.value}${time}` : "");
                    }} className="bg-secondary border-border h-8 text-sm" />
                  </div>
                  <div className="space-y-0.5">
                    <Input type="time" value={form.scheduled_at ? form.scheduled_at.split("T")[1] || "" : ""} onChange={(e) => {
                      const date = form.scheduled_at ? form.scheduled_at.split("T")[0] : new Date().toISOString().split("T")[0];
                      set("scheduled_at", e.target.value ? `${date}T${e.target.value}` : "");
                    }} className="bg-secondary border-border h-8 text-sm" />
                  </div>
                </div>
              </div>
            )}

            {/* Job fields */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Cuisine Type</Label>
                <Input value={form.cuisine_type} onChange={(e) => set("cuisine_type", e.target.value)} placeholder="Italian, Sushi..." className="bg-secondary border-border h-8 text-sm" />
              </div>
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Pay Rate</Label>
                <Input value={form.pay_rate} onChange={(e) => set("pay_rate", e.target.value)} placeholder="$25/hr" className="bg-secondary border-border h-8 text-sm" />
              </div>
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Hours</Label>
                <Input value={form.hours} onChange={(e) => set("hours", e.target.value)} placeholder="6pm–11pm" className="bg-secondary border-border h-8 text-sm" />
              </div>
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Experience</Label>
                <Select onValueChange={(v) => set("experience_level", v)}>
                  <SelectTrigger className="bg-secondary border-border h-8 text-xs">
                    <SelectValue placeholder="Level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="entry">Entry Level</SelectItem>
                    <SelectItem value="mid">2–5 Years</SelectItem>
                    <SelectItem value="senior">5+ Years</SelectItem>
                    <SelectItem value="executive">Executive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-0.5">
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Location</Label>
              <Input value={form.location} onChange={(e) => set("location", e.target.value)} placeholder="Downtown Chicago, IL" className="bg-secondary border-border h-8 text-sm" />
            </div>

            {/* Navigation */}
            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                onClick={() => navigate("feed")}
                className="flex-1 h-9 text-sm"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!canPost}
                className="flex-1 h-9 text-sm bg-primary text-primary-foreground ember-glow"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                    Posting...
                  </span>
                ) : "Post Now"}
              </Button>
            </div>
          </div>
        )}

        {/* Step: done */}
        {step === "done" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center mb-6 ember-glow">
              <CheckCircle size={40} className="text-primary" />
            </div>
            <h2 className="text-4xl text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>
              You're Live!
            </h2>
            <p className="text-muted-foreground text-sm mb-8">
              Your post is now visible to the community
            </p>
            <div className="space-y-3 w-full">
              <Button
                onClick={() => navigate("feed")}
                className="w-full bg-primary text-primary-foreground ember-glow"
              >
                Browse the Feed
              </Button>
              <Button
                variant="outline"
                onClick={resetAll}
                className="w-full"
              >
                Post Another
              </Button>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
