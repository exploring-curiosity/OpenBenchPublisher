import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const fastApiRes = await fetch(`${process.env.FASTAPI_URL || 'http://localhost:8000'}/api/start-full-run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await fastApiRes.json();

    if (!fastApiRes.ok) {
      return NextResponse.json({ detail: data.detail || 'FastAPI error' }, { status: fastApiRes.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error: any) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }
}
