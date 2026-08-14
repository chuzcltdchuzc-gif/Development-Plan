import { cn } from "@/lib/utils";

interface TrustScoreGaugeProps {
  score: number;
  className?: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function TrustScoreGauge({ score, className, size = "md", showLabel = true }: TrustScoreGaugeProps) {
  const normalizedScore = Math.max(0, Math.min(100, score));
  
  let riskLevel = "Concern";
  let colorClass = "text-destructive";
  let bgClass = "bg-destructive/10";
  let strokeClass = "stroke-destructive";
  
  if (normalizedScore >= 90) {
    riskLevel = "Excellent";
    colorClass = "text-primary";
    bgClass = "bg-primary/10";
    strokeClass = "stroke-primary";
  } else if (normalizedScore >= 70) {
    riskLevel = "Good";
    colorClass = "text-emerald-600";
    bgClass = "bg-emerald-600/10";
    strokeClass = "stroke-emerald-600";
  } else if (normalizedScore >= 40) {
    riskLevel = "Moderate";
    colorClass = "text-amber-500";
    bgClass = "bg-amber-500/10";
    strokeClass = "stroke-amber-500";
  }

  const dimensions = {
    sm: { svg: 48, stroke: 4, text: "text-sm", label: "text-[10px]" },
    md: { svg: 64, stroke: 6, text: "text-lg", label: "text-xs" },
    lg: { svg: 120, stroke: 10, text: "text-3xl", label: "text-sm" },
  };

  const { svg: d, stroke, text, label } = dimensions[size];
  const radius = (d - stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (normalizedScore / 100) * circumference;

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <div className="relative" style={{ width: d, height: d }}>
        <svg className="h-full w-full rotate-[-90deg]" viewBox={`0 0 ${d} ${d}`}>
          {/* Background circle */}
          <circle
            cx={d / 2}
            cy={d / 2}
            r={radius}
            className="stroke-muted fill-none"
            strokeWidth={stroke}
          />
          {/* Foreground circle */}
          <circle
            cx={d / 2}
            cy={d / 2}
            r={radius}
            className={cn("fill-none transition-all duration-1000 ease-in-out", strokeClass)}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("font-display font-bold leading-none", colorClass, text)}>
            {normalizedScore}
          </span>
        </div>
      </div>
      {showLabel && (
        <div className={cn("flex flex-col items-center", label)}>
          <span className="font-semibold text-muted-foreground uppercase tracking-wider">Trust Score</span>
          <span className={cn("font-medium", colorClass)}>{riskLevel}</span>
        </div>
      )}
    </div>
  );
}
