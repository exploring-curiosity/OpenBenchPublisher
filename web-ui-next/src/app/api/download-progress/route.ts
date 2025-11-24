import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const requestId = searchParams.get('request_id');
    
    if (!requestId) {
      return NextResponse.json(
        { error: 'request_id parameter is required' },
        { status: 400 }
      );
    }
    
    const res = await fetch(`http://localhost:8000/api/download-progress?request_id=${requestId}`, {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch download progress' },
        { status: res.status }
      );
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to connect to backend' },
      { status: 500 }
    );
  }
}
