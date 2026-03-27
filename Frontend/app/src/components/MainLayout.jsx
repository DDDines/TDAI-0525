/**
 * Module main layout.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const MOBILE_BREAKPOINT = 900;

function isMobileViewport() {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.innerWidth <= MOBILE_BREAKPOINT;
}

function MainLayout() {
  const mobileViewportRef = useRef(isMobileViewport());
  const [isMobileLayout, setIsMobileLayout] = useState(mobileViewportRef.current);
  const [sidebarOpen, setSidebarOpen] = useState(() => !mobileViewportRef.current);
  const location = useLocation();

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const handleResize = () => {
      const nextIsMobile = isMobileViewport();
      setIsMobileLayout(nextIsMobile);
      if (mobileViewportRef.current !== nextIsMobile) {
        mobileViewportRef.current = nextIsMobile;
        setSidebarOpen(!nextIsMobile);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    if (isMobileLayout) {
      setSidebarOpen(false);
    }
  }, [isMobileLayout, location.pathname]);

  const toggleSidebar = () => {
    setSidebarOpen((open) => !open);
  };

  return (
    <div
      className={`main-layout-root ${isMobileLayout ? 'mobile-layout' : 'desktop-layout'} ${
        sidebarOpen ? 'sidebar-open' : 'sidebar-closed'
      }`}
    >
      <Sidebar
        isOpen={sidebarOpen}
        isMobileViewport={isMobileLayout}
        toggleSidebar={toggleSidebar}
      />
      {isMobileLayout && sidebarOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Fechar menu"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <div className="main">
        <Topbar toggleSidebar={toggleSidebar} isMobileLayout={isMobileLayout} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default MainLayout;
