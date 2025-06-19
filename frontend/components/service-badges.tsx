import { Badge } from "@/components/ui/badge";
import { Youtube, Music2, Instagram } from "lucide-react";

const services = [
  { name: "YouTube", icon: Youtube, color: "text-red-500" },
  { name: "TikTok", icon: Music2, color: "text-foreground" },
  { name: "Instagram", icon: Instagram, color: "text-pink-500" },
];

export function ServiceBadges() {
  return (
    <div className="flex flex-col items-center gap-3">
      <span className="text-sm text-muted-foreground">supported platforms</span>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {services.map((service, index) => {
          const Icon = service.icon;
          return (
            <Badge
              key={service.name}
              variant="secondary"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary/80 animate-pop-in"
              style={{ animationDelay: `${index * 75}ms` }}
            >
              <Icon className={`h-3.5 w-3.5 ${service.color}`} />
              <span className="text-xs font-medium">{service.name}</span>
            </Badge>
          );
        })}
      </div>
    </div>
  );
}
