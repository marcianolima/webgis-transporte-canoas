import { WifiOff } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** Cartões e estados reutilizados pelas páginas da aplicação. */
export function Card({
  title,
  value,
  description,
  icon: Icon,
  tone = "",
}: {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  tone?: string;
}) {
  return (
    <article className={"metric " + tone}>
      <div className="metric-top">
        <span>{title}</span>
        <Icon size={19} />
      </div>
      <strong>{value}</strong>
      <p>{description}</p>
    </article>
  );
}
export function Panel({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Empty({
  title,
  children,
  icon: Icon = WifiOff,
}: {
  title: string;
  children: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={25} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
