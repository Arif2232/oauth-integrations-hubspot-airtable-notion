import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { IntegrationForm } from './integration-form';

vi.mock('axios', () => ({ default: { post: vi.fn() } }));

test('requires a user before opening authorization', () => {
  render(<IntegrationForm />);
  fireEvent.change(screen.getByLabelText('User'), { target: { value: '' } });
  fireEvent.click(screen.getByRole('button', { name: /connect hubspot/i }));
  expect(screen.getByRole('alert').textContent).toMatch(/enter a user and workspace/i);
});
