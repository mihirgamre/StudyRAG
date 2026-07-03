import { LogOut, Plus } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Course } from '../types';

interface CoursesPageProps {
  token: string;
  onOpenCourse: (course: Course) => void;
  onLogout: () => void;
}

export function CoursesPage({ token, onOpenCourse, onLogout }: CoursesPageProps) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadCourses();
  }, []);

  async function loadCourses() {
    try {
      setCourses(await api.listCourses(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load courses');
    }
  }

  async function createCourse(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }
    setError(null);
    try {
      const course = await api.createCourse(token, name.trim());
      setCourses((current) => [...current, course]);
      setName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create course');
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Courses</h1>
          <p>Choose a course workspace.</p>
        </div>
        <button className="icon-button" type="button" onClick={onLogout} aria-label="Log out">
          <LogOut size={18} aria-hidden />
        </button>
      </header>

      <section className="section-band">
        <form className="inline-form" onSubmit={createCourse}>
          <input value={name} placeholder="Course name" onChange={(event) => setName(event.target.value)} />
          <button className="primary-button" type="submit">
            <Plus size={16} aria-hidden />
            Create
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="course-grid">
        {courses.map((course) => (
          <button className="course-card" type="button" key={course.id} onClick={() => onOpenCourse(course)}>
            <strong>{course.name}</strong>
            <span>Open workspace</span>
          </button>
        ))}
      </section>
    </main>
  );
}
