import { useState, useRef } from "react";
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
import { CheckCircle, Upload, X, Image as ImageIcon, VideoIcon, Tag, Calendar, Sparkles, Lightbulb, Clock, Star, HardHat, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import LiveRecorder from "./LiveRecorder";

type Step = "create" | "record" | "done";

export default function PostScreen() {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const isAdmin = user?.is_admin ?? false;
  const [step, setStep] = useState<Step>("create");
  const [postType] = useState<"worker" | "employer">(
    user?.role === "employer" ? "employer" : "worker"
  );

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

  const [form, setForm] = useState({
    title: "",
    description: "",
    cuisine_type: "",
    pay_rate: "",
    hours: "",
    experience_level: "",
    location: "",
    category: "general",
    price: "",
    event_date: "",
    event_time: "",
    scheduled_at: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementAccepted, setAgreementAccepted] = useState(user?.advertiser_agreement_accepted ?? false);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
        <p className="text-muted-foreground">Sign in to post</p>
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
    setStep(isAdmin ? "create" : "record");
    setRecordedBlob(null);
    setRecordedUrl("");
    setUploadedVideoUrl("");
    resetImage();
    resetVideo();
    setAspectRatio("9:16");
    setForm({ title: "", description: "", cuisine_type: "", pay_rate: "", hours: "", experience_level: "", location: "", category: "general", price: "", event_date: "", event_time: "", scheduled_at: "" });
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
      setStep("create");
    } finally {
      setSubmitting(false);
    }
  };

  const acceptAgreement = async () => {
    try {
      const res = await fetch("/api/advertiser/agreement", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setAgreementAccepted(true);
        setShowAgreement(false);
      }
    } catch {}
  };

  const handleSubmit = async () => {
    // Advertiser must accept agreement before first post
    if (user?.is_advertiser && !agreementAccepted) {
      setShowAgreement(true);
      return;
    }
    doSubmit();
  };

  const doSubmit = async () => {
    setSubmitting(true);
    try {
      const fd = new FormData();

      if (isAdmin) {
        // Admin post: unified — can have text + image + video
        fd.append("type", postType);
        fd.append("post_type", uploadedVideoUrlAdmin ? "video" : uploadedImageUrl ? "image" : "text");
        fd.append("category", form.category);
        fd.append("price", form.price);
        fd.append("event_date", form.event_date);
        fd.append("event_time", form.event_time);
        fd.append("scheduled_at", form.scheduled_at);
        fd.append("aspect_ratio", aspectRatio);
        fd.append("title", form.title);
        fd.append("description", form.description);
        fd.append("video_url", uploadedVideoUrlAdmin || "");
        fd.append("image_url", uploadedImageUrl || "");
      } else {
        // Regular user: can have text + image + video
        fd.append("type", postType);
        fd.append("post_type", uploadedVideoUrlAdmin ? "video" : uploadedImageUrl ? "image" : "text");
        fd.append("category", form.category);
        fd.append("price", form.price);
        fd.append("event_date", form.event_date);
        fd.append("event_time", form.event_time);
        fd.append("scheduled_at", form.scheduled_at);
        fd.append("aspect_ratio", aspectRatio);
        fd.append("title", form.title);
        fd.append("description", form.description);
        fd.append("video_url", uploadedVideoUrlAdmin || "");
        fd.append("image_url", uploadedImageUrl || "");
        
        // Extra metadata fields for regular users
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
        setStep("done");
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(errorData.detail || "Failed to post. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Determine if post is valid
  // Requires: Description AND at least one of (Image OR Video)
  const canPost = Boolean(
    form.description.trim() && 
    (uploadedImageUrl || uploadedVideoUrlAdmin) && 
    !submitting
  );

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      {/* Progress bar */}
      <div className="h-1 bg-secondary">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{
            width: step === "create" ? "50%" : step === "record" ? "50%" : "100%",
          }}
        />
      </div>

      <div className="p-4">
        {/* Step: record — non-admin camera recording */}
        {step === "record" && !isAdmin && (
          <div className="space-y-4">
            <div>
              <h2 className="text-3xl text-foreground mb-1" style={{ fontFamily: "'Bebas Neue'" }}>
                Record Your Video
              </h2>
              <p className="text-muted-foreground text-sm">
                Speak directly to {postType === "worker" ? "spots" : "crew"} — up to 60 seconds
              </p>
            </div>

            {submitting ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
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
                onRecorded={handleRecorded}
                onCancel={() => navigate("feed")}
              />
            )}
          </div>
        )}

        {/* Step: create — admin unified post OR non-admin details */}
        {step === "create" && (
          <div className="space-y-3">
            <div className="flex items-baseline justify-between">
              <div>
                <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
                  Create a Post
                </h2>
                <p className="text-muted-foreground text-[11px]">
                  <span className="text-amber-500 font-semibold"><Lightbulb size={11} className="inline mr-0.5" />Video posts get 3x more matches!</span>
                </p>
              </div>
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
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} className="hidden" />
                  <div className={cn("w-full rounded-xl overflow-hidden border transition-all duration-300", imagePreview ? "border-border bg-black" : "border-2 border-dashed border-border hover:border-primary/50 hover:bg-secondary/50 bg-secondary/20")}>
                    <div className="w-full max-h-44 flex items-center justify-center overflow-hidden">
                      {imagePreview ? (
                        <div className="relative w-full h-full">
                          <img src={imagePreview} alt="Preview" className="w-full h-full object-cover max-h-44" />
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
                    <div className="w-full max-h-44 flex items-center justify-center overflow-hidden">
                      {videoPreviewAdmin ? (
                        <div className="relative w-full h-full">
                          <video src={videoPreviewAdmin} controls className="w-full h-full object-cover max-h-44" />
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
              </div>
            </div>

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
                    <SelectItem value="general"><Sparkles size={12} className="inline mr-1" /> General</SelectItem>
                    <SelectItem value="crew"><HardHat size={12} className="inline mr-1" /> Crew</SelectItem>
                    <SelectItem value="kitchen"><Building2 size={12} className="inline mr-1" /> Kitchen</SelectItem>
                    <SelectItem value="sale"><Tag size={12} className="inline mr-1" /> For Sale</SelectItem>
                    <SelectItem value="event"><Calendar size={12} className="inline mr-1" /> Event</SelectItem>
                    {isAdmin && (
                      <SelectItem value="sponsored"><Star size={12} className="inline mr-1 fill-primary text-primary" /> Sponsored</SelectItem>
                    )}
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

            {/* Schedule Post — advertisers & admins only */}
            {(user?.is_advertiser || isAdmin) && (
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

      {/* Advertiser Agreement Modal */}
      {showAgreement && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-card border border-border rounded-2xl max-w-sm w-full p-6 space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="text-center">
              <span className="text-3xl">✦</span>
              <h3 className="text-xl text-foreground mt-2" style={{ fontFamily: "'Bebas Neue'" }}>
                Advertiser Terms & Conditions
              </h3>
            </div>
            <div className="text-xs text-muted-foreground space-y-2 leading-relaxed">
              <p className="text-foreground font-medium">PLEASE READ CAREFULLY. BY CLICKING "I AGREE," YOU BIND YOURSELF TO THESE TERMS.</p>
              
              <p><strong className="text-foreground">1. Content Responsibility.</strong> Advertiser assumes full and exclusive responsibility for all uploaded content, including but not limited to videos, images, text, and any other media. Advertiser represents and warrants that they possess all necessary rights, licenses, and permissions to use, reproduce, and distribute such content.</p>
              
              <p><strong className="text-foreground">2. Quality Standards.</strong> All submitted media shall be of commercially reasonable quality, including but not limited to proper lighting, clear resolution, and audible sound. Day Shift reserves the right, in its sole discretion, to reject or remove any content that fails to meet these standards, without obligation of refund.</p>
              
              <p><strong className="text-foreground">3. Prohibited Content.</strong> Advertiser shall not upload, publish, or transmit any content that: (a) constitutes hate speech, discrimination, or harassment based on race, ethnicity, religion, gender, sexual orientation, or disability; (b) depicts nudity, sexual content, or graphic violence; (c) promotes illegal activities; (d) contains inappropriate, obscene, or offensive material; or (e) infringes upon the intellectual property rights of any third party. Violation shall result in immediate content removal, forfeiture of any fees paid, and potential permanent account suspension.</p>
              
              <p><strong className="text-foreground">4. Disclaimer of Liability.</strong> DAY SHIFT, ITS OFFICERS, DIRECTORS, EMPLOYEES, AND AFFILIATES SHALL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF OR RELATED TO ADVERTISER'S CONTENT, INCLUDING BUT NOT LIMITED TO CLAIMS OF FALSE ADVERTISING, DEFAMATION, INTELLECTUAL PROPERTY INFRINGEMENT, OR ANY OTHER CAUSE OF ACTION.</p>
              
              <p><strong className="text-foreground">5. Compliance with Laws.</strong> Advertiser shall comply with all applicable federal, state, and local laws, rules, and regulations, including without limitation the Federal Trade Commission's advertising disclosure guidelines and all applicable consumer protection statutes.</p>
              
              <p><strong className="text-foreground">6. Content Removal Rights.</strong> Day Shift retains the absolute right to refuse, modify, or remove any content at any time, for any reason or no reason, without prior notice, consent, or refund of any fees.</p>
              
              <p><strong className="text-foreground">7. Indemnification.</strong> Advertiser shall indemnify, defend, and hold harmless Day Shift and its officers, directors, employees, and agents from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising out of or related to Advertiser's content or breach of these Terms.</p>
              
              <p><strong className="text-foreground">8. No Warranties.</strong> DAY SHIFT PROVIDES ITS SERVICES "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. DAY SHIFT DOES NOT GUARANTEE ANY SPECIFIC NUMBER OF VIEWS, ENGAGEMENT METRICS, CLICKS, OR OTHER OUTCOMES.</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowAgreement(false)}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                onClick={acceptAgreement}
              >
                I Agree
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
