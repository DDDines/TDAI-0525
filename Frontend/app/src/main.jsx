/**
 * Module main.
 *
 * Defines responsibilities and integration points for frontend.
 */

// Frontend/app/src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import App from './App.jsx';
import { appQueryClient } from './lib/queryClient.js';
import './index.css';

const rootElement = document.getElementById('root');
const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <QueryClientProvider client={appQueryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
