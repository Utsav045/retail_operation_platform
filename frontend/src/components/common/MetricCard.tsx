import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Info } from 'lucide-react';
import { Tooltip } from './Tooltip';

interface MetricCardProps {
  title: string;
  value: string | number;
  subValue?: string;
  tooltipText: string;
  icon?: LucideIcon;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subValue,
  tooltipText,
  icon: Icon,
  variant = 'default',
}) => {
  const borderStyles = {
    default: 'border-slate-200 dark:border-slate-800',
    success: 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/20 dark:bg-emerald-950/20',
    warning: 'border-amber-200 dark:border-amber-900/50 bg-amber-50/20 dark:bg-amber-950/20',
    danger: 'border-rose-200 dark:border-rose-900/50 bg-rose-50/20 dark:bg-rose-950/20',
  };

  return (
    <div className={`p-4 bg-white dark:bg-slate-900 rounded-lg border ${borderStyles[variant]} shadow-sm transition-all duration-150`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </span>
        <div className="flex items-center gap-1.5">
          {Icon && <Icon className="w-4 h-4 text-slate-400 dark:text-slate-500" />}
          <Tooltip content={tooltipText}>
            <button type="button" aria-label="Info" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
              <Info className="w-3.5 h-3.5" />
            </button>
          </Tooltip>
        </div>
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white font-mono">
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {subValue}
          </span>
        )}
      </div>
    </div>
  );
};
