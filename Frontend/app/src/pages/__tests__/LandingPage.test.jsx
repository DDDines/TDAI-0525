import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LandingPage from '../LandingPage.jsx';

describe('LandingPage', () => {
  test('renders the real logo, hero copy and public CTAs', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

    expect(screen.getByAltText(/CommerceFolio logo/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Transforme catálogos brutos em/i })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Começar grátis/i })[0]).toHaveAttribute('href', '/signup');
    expect(screen.getAllByRole('link', { name: /Entrar/i })[0]).toHaveAttribute('href', '/login');
    expect(screen.getByText(/SaaS RPA para catálogos/i)).toBeInTheDocument();
  });
});
