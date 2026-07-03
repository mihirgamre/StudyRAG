import { UploadCloud } from 'lucide-react';
import { useRef, useState } from 'react';

interface UploadDropzoneProps {
  disabled?: boolean;
  onUpload: (file: File) => Promise<void>;
}

export function UploadDropzone({ disabled, onUpload }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file?: File) {
    if (!file || disabled || uploading) {
      return;
    }
    setUploading(true);
    try {
      await onUpload(file);
    } finally {
      setUploading(false);
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    }
  }

  return (
    <div
      className={`upload-dropzone ${dragging ? 'dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        void handleFile(event.dataTransfer.files[0]);
      }}
    >
      <UploadCloud size={22} aria-hidden />
      <div>
        <strong>{uploading ? 'Uploading...' : 'Upload course file'}</strong>
        <span>PDF, DOCX, or TXT</span>
      </div>
      <button type="button" className="secondary-button" disabled={disabled || uploading} onClick={() => inputRef.current?.click()}>
        Choose file
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        hidden
        onChange={(event) => void handleFile(event.target.files?.[0])}
      />
    </div>
  );
}
