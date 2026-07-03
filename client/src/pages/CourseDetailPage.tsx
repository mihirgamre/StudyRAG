import { ArrowLeft, MessageSquare } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DocumentStatusIndicator } from '../components/DocumentStatusIndicator';
import { UploadDropzone } from '../components/UploadDropzone';
import type { Course, CourseDocument } from '../types';

interface CourseDetailPageProps {
  token: string;
  course: Course;
  onBack: () => void;
  onOpenChat: (course: Course) => void;
}

export function CourseDetailPage({ token, course, onBack, onOpenChat }: CourseDetailPageProps) {
  const [documents, setDocuments] = useState<CourseDocument[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDocuments();
  }, [course.id]);

  useEffect(() => {
    const activeDocuments = documents.filter((document) => document.status === 'pending' || document.status === 'chunked');
    if (activeDocuments.length === 0) {
      return;
    }

    const timer = window.setInterval(() => {
      void Promise.all(activeDocuments.map((document) => api.getDocumentStatus(token, document.id)))
        .then((updated) => {
          setDocuments((current) =>
            current.map((document) => updated.find((nextDocument) => nextDocument.id === document.id) ?? document),
          );
        })
        .catch((err) => setError(err instanceof Error ? err.message : 'Could not refresh document status'));
    }, 1800);

    return () => window.clearInterval(timer);
  }, [documents, token]);

  async function loadDocuments() {
    try {
      setDocuments(await api.listDocuments(token, course.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load documents');
    }
  }

  async function upload(file: File) {
    setError(null);
    try {
      const document = await api.uploadDocument(token, course.id, file);
      setDocuments((current) => [document, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="icon-button" type="button" onClick={onBack} aria-label="Back to courses">
          <ArrowLeft size={18} aria-hidden />
        </button>
        <div>
          <h1>{course.name}</h1>
          <p>Documents</p>
        </div>
        <button className="primary-button" type="button" onClick={() => onOpenChat(course)}>
          <MessageSquare size={16} aria-hidden />
          Chat
        </button>
      </header>

      <section className="section-band">
        <UploadDropzone onUpload={upload} />
        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="document-table" aria-label="Uploaded documents">
        <div className="table-row table-head">
          <span>File</span>
          <span>Type</span>
          <span>Status</span>
        </div>
        {documents.map((document) => (
          <div className="table-row" key={document.id}>
            <span className="truncate">{document.filename}</span>
            <span>{document.source_type}</span>
            <DocumentStatusIndicator status={document.status} />
          </div>
        ))}
      </section>
    </main>
  );
}
