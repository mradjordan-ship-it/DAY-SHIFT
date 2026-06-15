// PWA install prompt type (not in standard TS libs)
export interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export type ApiStatus = "checking" | "connected" | "error";

export interface HealthResponse {
  ok: boolean;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: "worker" | "employer";
  is_admin: boolean;
  is_advertiser: boolean;
  advertiser_agreement_accepted: boolean;
  onboarded: boolean;
  email_verified: boolean;
  bio: string;
  avatar_url: string;
  avg_rating: number;
  total_shifts: number;
  created_at: string;
}

export interface Video {
  id: number;
  user_id: number;
  video_url: string | null;
  image_url: string | null;
  thumbnail_url: string;
  type: "worker" | "employer";
  post_type: "video" | "image" | "text";
  category: "general" | "sale" | "event" | "crew" | "kitchen";
  price: string;
  event_date: string;
  event_time: string;
  aspect_ratio: "9:16" | "1:1" | "4:5" | "16:9";
  title: string | null;
  description: string;
  cuisine_type: string;
  pay_rate: string;
  hours: string;
  experience_level: string;
  location: string;
  likes: number;
  scheduled_at: string | null;
  created_at: string;
  author_name: string;
  author_avatar: string;
  author_rating: number;
  author_role: string;
  author_is_admin: boolean;
  author_is_advertiser: boolean;
  liked_by_me: boolean;
  is_sponsored?: boolean;
}

export interface Match {
  id: number;
  worker_id: number;
  employer_id: number;
  worker_video_id: number;
  employer_video_id: number;
  status: "pending" | "active" | "completed" | "cancelled";
  initiated_by: number;
  worker_confirmed: boolean;
  employer_confirmed: boolean;
  created_at: string;
  worker_name: string;
  worker_avatar: string;
  employer_name: string;
  employer_avatar: string;
  employer_location?: string;
}

export interface Message {
  id: number;
  match_id: number;
  sender_id: number;
  content: string;
  created_at: string;
  sender_name: string;
  sender_avatar: string;
}

export interface Review {
  id: number;
  match_id: number;
  reviewer_id: number;
  reviewee_id: number;
  rating: number;
  feedback: string;
  created_at: string;
  reviewer_name: string;
  reviewer_avatar: string;
}

export type Screen =
  | "feed"
  | "post"
  | "matches"
  | "chat"
  | "profile"
  | "login"
  | "register"
  | "forgot"
  | "reset"
  | "verify-email"
  | "user-profile"
  | "review"
  | "admin"
  | "support"
  | "sponsor"
  | "terms"
  | "privacy"
  | "onboarding"
  | "about"
  | "boost"
  | "analytics"
  | "landing";

export interface PostBoost {
  id: number;
  video_id: number;
  user_id: number;
  tier: "boost" | "spotlight" | "premium";
  status: "pending" | "active" | "expired" | "rejected";
  start_date: string | null;
  end_date: string | null;
  stripe_session_id?: string;
  stripe_payment_intent_id?: string;
  payment_status: "unpaid" | "paid" | "failed" | "refunded";
  admin_approved: boolean;
  created_at: string;
  video_title?: string;
  thumbnail_url?: string;
}

export interface AdvertiserSubscription {
  id: number;
  user_id: number;
  tier: "free" | "boost" | "spotlight" | "premium";
  start_date: string;
  end_date: string | null;
  boosts_used: number;
  boosts_remaining: number;
  free_boost_used: boolean;
  payment_method: string;
  status: string;
  created_at: string;
}

export type FeedTab = "all" | "workers" | "employers";
