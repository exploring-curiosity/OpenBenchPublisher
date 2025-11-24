import { NextResponse } from 'next/server';

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    const res = await fetch(`http://localhost:8000/api/datasets/${id}`, {
      method: 'DELETE',
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to delete dataset' },
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
