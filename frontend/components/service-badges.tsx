import { Badge } from "@/components/ui/badge";
import { Youtube, Music2, Instagram } from "lucide-react";

const services = [
  { name: "YouTube", icon: Youtube, color: "text-red-500" },
  { name: "TikTok", icon: Music2, color: "text-black dark:text-white" },
  { name: "Instagram", icon: Instagram, color: "text-pink-500" },
];

export function ServiceBadges() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <span className="text-sm text-muted-foreground">Supported:</span>
      {services.map((service) => {
        const Icon = service.icon;
        return (
          <Badge
            key={service.name}
            variant="secondary"
            className="flex items-center gap-1.5 px-3 py-1"
          >
            <Icon className={`h-3.5 w-3.5 ${service.color}`} />
            <span>{service.name}</span>
          </Badge>
        );
      })}
    </div>
  );
}
