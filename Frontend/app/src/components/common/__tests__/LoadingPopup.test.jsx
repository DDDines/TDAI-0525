import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingPopup from '../LoadingPopup.jsx';

describe('LoadingPopup', () => {
  test('renders popup when open with logo, progress, details and chips', () => {
    render(
      <LoadingPopup
        isOpen={true}
        title="Importando"
        message="Loading test"
        progressPercent={67.4}
        progressLabel="2/3 páginas"
        details={['fase 1', '', 'fase 2']}
        chips={[
          { label: 'Status', value: 'PROCESSING' },
          { label: 'Arquivo', value: '  ' },
          { label: 'Tempo', value: 0 },
        ]}
      />
    );

    expect(screen.getByAltText('CatalogAI')).toBeInTheDocument();
    expect(screen.getByText('Loading test')).toBeInTheDocument();
    expect(screen.getByText('67%')).toBeInTheDocument();
    expect(screen.getByText('2/3 páginas')).toBeInTheDocument();
    expect(screen.getByText('fase 1')).toBeInTheDocument();
    expect(screen.getByText('fase 2')).toBeInTheDocument();
    expect(screen.getByText('PROCESSING')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  test('uses defaults, filters invalid collections and omits optional blocks when not applicable', () => {
    render(
      <LoadingPopup
        isOpen={true}
        details="nao-array"
        chips={{ status: 'PROCESSING' }}
        progressPercent={Infinity}
      />
    );

    expect(screen.getByText('Processando')).toBeInTheDocument();
    expect(screen.getByText('Carregando...')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.queryByText(/Atualizações em tempo real/i)).not.toBeInTheDocument();
  });

  test('renders nothing when the popup is closed', () => {
    const { container } = render(<LoadingPopup isOpen={false} message="Hidden" />);

    expect(container).toBeEmptyDOMElement();
  });
});
