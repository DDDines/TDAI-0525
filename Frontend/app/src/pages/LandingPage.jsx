/**
 * Module landing page.
 *
 * Presents the public marketing surface and first conversion path into
 * CommerceFolio authentication flows.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import LogoImg from '../assets/Logo.png';
import './LandingPage.css';

const features = [
  {
    icon: '01',
    title: 'Importação inteligente',
    desc: 'Suba PDF, XLSX ou CSV. O sistema detecta regiões, mapeia colunas e prepara o catálogo para revisão.',
  },
  {
    icon: '02',
    title: 'Geração e enrichment',
    desc: 'Gere títulos, descrições e versões por canal com GPT-4o, Gemini e regras do seu catálogo.',
  },
  {
    icon: '03',
    title: 'Saída pronta para operar',
    desc: 'Revise, aprove, exporte e acompanhe o fluxo do produto sem depender de planilhas espalhadas.',
  },
];

const metrics = [
  { value: 'PDF + XLSX', label: 'Entrada do catálogo' },
  { value: 'Multi-canal', label: 'Google, ML, B2B e e-commerce' },
  { value: 'Export XLSX', label: 'Saída pronta' },
];

const plans = [
  {
    name: 'Grátis',
    price: 'R$ 0',
    period: '/mês',
    features: ['50 produtos', '10 enriquecimentos/mês', '20 gerações IA/mês'],
    cta: 'Começar grátis',
    href: '/signup',
    highlight: false,
  },
  {
    name: 'Pro',
    price: 'R$ 97',
    period: '/mês',
    features: ['Produtos ilimitados', '500 enriquecimentos/mês', '1000 gerações IA/mês', 'Suporte prioritário'],
    cta: 'Assinar Pro',
    href: '/signup?plano=pro',
    highlight: true,
  },
];

export default function LandingPage() {
  return (
    <div className="lp-root">
      <header className="lp-nav">
        <div className="lp-nav-shell">
          <Link to="/landing" className="lp-brand" aria-label="CommerceFolio">
            <span className="lp-brand-mark">
              <img src={LogoImg} alt="CommerceFolio logo" />
            </span>
            <span className="lp-brand-text">
              <strong>CommerceFolio</strong>
              <small>SaaS RPA para catálogos</small>
            </span>
          </Link>

          <div className="lp-nav-links">
            <a href="#features">Funcionalidades</a>
            <a href="#pricing">Planos</a>
            <Link to="/login" className="lp-btn-outline">Entrar</Link>
            <Link to="/signup" className="lp-btn-primary">Criar conta</Link>
          </div>
        </div>
      </header>

      <main className="lp-main">
        <section className="lp-hero">
          <div className="lp-hero-shell">
            <div className="lp-hero-copy">
              <span className="lp-eyebrow">Catálogos prontos para vender</span>
              <h1>
                Transforme catálogos brutos em
                <span className="lp-accent"> produtos prontos com IA</span>
              </h1>
              <p className="lp-hero-sub">
                Importe catálogos de fornecedores, revise os dados, gere conteúdo com IA e exporte tudo
                pronto para operar em um fluxo único.
              </p>

              <div className="lp-metrics">
                {metrics.map((metric) => (
                  <div key={metric.label} className="lp-metric-card">
                    <strong>{metric.value}</strong>
                    <span>{metric.label}</span>
                  </div>
                ))}
              </div>

              <div className="lp-hero-ctas">
                <Link to="/signup" className="lp-btn-primary lp-btn-lg">Começar grátis</Link>
                <Link to="/login" className="lp-btn-outline lp-btn-lg">Já tenho conta</Link>
              </div>
            </div>

            <div className="lp-hero-visual">
              <div className="lp-showcase-card">
                <div className="lp-showcase-badge">
                  <img src={LogoImg} alt="" aria-hidden="true" />
                  <div>
                    <strong>Fluxo completo</strong>
                    <span>Importe, revise, gere e exporte</span>
                  </div>
                </div>

                <div className="lp-mockup">
                  <div className="lp-mockup-bar">
                    <span />
                    <span />
                    <span />
                  </div>
                  <div className="lp-mockup-body">
                    <div className="lp-mockup-header" />
                    {[1, 2, 3, 4, 5].map((item) => (
                      <div key={item} className="lp-mockup-row">
                        <div className="lp-mockup-cell lp-cell-img" />
                        <div className="lp-mockup-cell lp-cell-wide" />
                        <div className="lp-mockup-cell lp-cell-mid" />
                        <div className="lp-mockup-cell lp-cell-badge" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="lp-section" id="features">
          <div className="lp-section-shell">
            <h2 className="lp-section-title">Tudo que você precisa para operar catálogo com escala</h2>
            <div className="lp-features">
              {features.map((feature) => (
                <article key={feature.title} className="lp-feature-card">
                  <span className="lp-feature-icon">{feature.icon}</span>
                  <h3>{feature.title}</h3>
                  <p>{feature.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section lp-section-dark" id="pricing">
          <div className="lp-section-shell">
            <h2 className="lp-section-title">Planos simples para começar</h2>
            <div className="lp-plans">
              {plans.map((plan) => (
                <article key={plan.name} className={`lp-plan-card ${plan.highlight ? 'lp-plan-highlight' : ''}`}>
                  {plan.highlight ? <span className="lp-plan-badge">Mais popular</span> : null}
                  <h3>{plan.name}</h3>
                  <div className="lp-plan-price">
                    <strong>{plan.price}</strong>
                    <span>{plan.period}</span>
                  </div>
                  <ul>
                    {plan.features.map((feature) => (
                      <li key={feature}>
                        <span className="lp-check">OK</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to={plan.href} className={plan.highlight ? 'lp-btn-primary' : 'lp-btn-outline'}>
                    {plan.cta}
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-footer-shell">
          <div className="lp-footer-brand">
            <span className="lp-brand-mark lp-brand-mark--small">
              <img src={LogoImg} alt="" aria-hidden="true" />
            </span>
            <div>
              <strong>CommerceFolio</strong>
              <span>Catálogo pronto para operar</span>
            </div>
          </div>
          <div className="lp-footer-links">
            <Link to="/landing">Início</Link>
            <Link to="/login">Entrar</Link>
            <Link to="/signup">Criar conta</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
