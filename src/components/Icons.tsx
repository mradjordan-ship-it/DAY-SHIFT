// Reusable role/category icons for consistency across the app
import { ChefHat, Store, Calendar, Tag, Shield, User } from "lucide-react";

export function CrewIcon({ className = "w-4 h-4" }: { className?: string }) {
  return <ChefHat className={className} />;
}

export function KitchenIcon({ className = "w-4 h-4" }: { className?: string }) {
  return <Store className={className} />;
}

export function EventIcon({ className = "w-4 h-4" }: { className?: string }) {
  return <Calendar className={className} />;
}

export function SaleIcon({ className = "w-4 h-4" }: { className?: string }) {
  return <Tag className={className} />;
}

export function AdminIcon({ className = "w-4 h-4" }: { className?: string }) {
  return <Shield className={className} />;
}

export function RoleIcon({ role, className = "w-4 h-4" }: { role: "worker" | "employer" | "admin"; className?: string }) {
  if (role === "admin") return <Shield className={className} />;
  if (role === "worker") return <ChefHat className={className} />;
  return <Store className={className} />;
}

export function CategoryIcon({ category, className = "w-4 h-4" }: { category: "sale" | "event" | "general"; className?: string }) {
  if (category === "sale") return <Tag className={className} />;
  if (category === "event") return <Calendar className={className} />;
  return null;
}
