import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    // Fetch the file from the backend
    const res = await fetch(`http://localhost:8000/download/${id}`);
    
    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to download dataset' },
        { status: res.status }
      );
    }
    
    // Get the file as a blob
    const blob = await res.blob();
    
    // Get the filename from the Content-Disposition header or use default
    const contentDisposition = res.headers.get('Content-Disposition');
    let filename = `dataset_${id}.zip`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    // Ensure filename ends with .zip
    if (!filename.endsWith('.zip')) {
      filename = `${filename}.zip`;
    }
    
    // Return the file as a download
    return new NextResponse(blob, {
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Download error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend' },
      { status: 500 }
    );
  }
}
