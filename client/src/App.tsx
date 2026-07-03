import { useMemo, useState } from 'react';
import { ChatPage } from './pages/ChatPage';
import { CourseDetailPage } from './pages/CourseDetailPage';
import { CoursesPage } from './pages/CoursesPage';
import { LoginPage } from './pages/LoginPage';
import type { Course } from './types';

type View = 'login' | 'courses' | 'course' | 'chat';

const tokenStorageKey = 'studyrag_token';

export function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenStorageKey));
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [view, setView] = useState<View>(() => (localStorage.getItem(tokenStorageKey) ? 'courses' : 'login'));

  const activeView = useMemo(() => {
    if (!token) {
      return 'login';
    }
    if (!selectedCourse && (view === 'course' || view === 'chat')) {
      return 'courses';
    }
    return view;
  }, [selectedCourse, token, view]);

  function authenticated(nextToken: string) {
    localStorage.setItem(tokenStorageKey, nextToken);
    setToken(nextToken);
    setView('courses');
  }

  function logout() {
    localStorage.removeItem(tokenStorageKey);
    setToken(null);
    setSelectedCourse(null);
    setView('login');
  }

  if (activeView === 'login' || !token) {
    return <LoginPage onAuthenticated={authenticated} />;
  }

  if (activeView === 'course' && selectedCourse) {
    return (
      <CourseDetailPage
        token={token}
        course={selectedCourse}
        onBack={() => setView('courses')}
        onOpenChat={(course) => {
          setSelectedCourse(course);
          setView('chat');
        }}
      />
    );
  }

  if (activeView === 'chat' && selectedCourse) {
    return <ChatPage token={token} course={selectedCourse} onBack={() => setView('course')} />;
  }

  return (
    <CoursesPage
      token={token}
      onLogout={logout}
      onOpenCourse={(course) => {
        setSelectedCourse(course);
        setView('course');
      }}
    />
  );
}
