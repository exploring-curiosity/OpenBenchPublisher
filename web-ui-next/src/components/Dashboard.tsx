"use client";

import { useState } from 'react';
import { BuildForm } from './BuildForm';
import { PlanOverview } from './PlanOverview';
import { FullDownload } from './FullDownload';

export function Dashboard() {
  const [plan, setPlan] = useState<any>(null);
  const [samples, setSamples] = useState<any[]>([]);
  const [requestId, setRequestId] = useState<string | null>(null);

  const handlePlanAndSample = (data: any) => {
    setPlan(data.plan);
    setSamples(data.samples);
    setRequestId(data.request_id);
  };

  return (
    <div className="space-y-8">
      <section className="grid gap-6 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:gap-8">
        <BuildForm onPlanAndSample={handlePlanAndSample} />
        <PlanOverview plan={plan} samples={samples} />
      </section>

      {requestId && <FullDownload requestId={requestId} />}
    </div>
  );
}
