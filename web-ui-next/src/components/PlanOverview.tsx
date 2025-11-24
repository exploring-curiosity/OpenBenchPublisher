"use client";

interface Plan {
  type: string;
  classes: string[];
  total: number;
}

interface Sample {
  url: string;
  title: string;
}

interface PlanOverviewProps {
  plan: Plan | null;
  samples: Sample[] | null;
}

export function PlanOverview({ plan, samples }: PlanOverviewProps) {
  if (!plan) {
    return (
        <div className="group relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:border-fuchsia-500/30">
            <div className="absolute inset-0 bg-gradient-to-bl from-fuchsia-500/5 to-cyan-500/5 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-fuchsia-100 md:text-sm">
                  <span className="h-1.5 w-1.5 rounded-full bg-fuchsia-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]" />
                  Plan & Samples
                </h2>
                <p className="mt-2 text-xs font-medium text-slate-400 md:text-sm">
                  Run "Plan & Preview" to see the generated plan and data samples.
                </p>
              </div>
            </div>
        </div>
    );
  }

  return (
    <div className="group relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:border-fuchsia-500/30">
        <div className="absolute inset-0 bg-gradient-to-bl from-fuchsia-500/5 to-cyan-500/5 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
        <div className="flex items-center justify-between gap-3">
            <div>
                <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-fuchsia-100 md:text-sm">
                    <span className="h-1.5 w-1.5 rounded-full bg-fuchsia-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]" />
                    Plan & Samples
                </h2>
            </div>
        </div>
        <div className="relative mt-6 space-y-4">
            <div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Plan Details</h3>
                <div className="mt-2 space-y-1 text-sm text-slate-300">
                    <p><strong>Type:</strong> {plan.type}</p>
                    <p><strong>Total Items:</strong> {plan.total}</p>
                    <p><strong>Classes:</strong> {plan.classes.join(', ')}</p>
                </div>
            </div>
            <div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Samples</h3>
                <div className="mt-2 space-y-2">
                    {samples && samples.map((sample, index) => (
                        <div key={index} className="rounded-lg border border-white/10 bg-slate-900/50 p-2 text-xs">
                            <p className="font-semibold truncate">{sample.title}</p>
                            <a href={sample.url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline truncate">{sample.url}</a>
                        </div>
                    ))}
                    {(!samples || samples.length === 0) && (
                        <p className="text-xs text-slate-500">No samples returned.</p>
                    )}
                </div>
            </div>
        </div>
    </div>
  );
}
