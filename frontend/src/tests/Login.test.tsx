import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

// Must mock BEFORE importing the component module
vi.mock('../services/api', () => ({
  authApi: {
    login: vi.fn<() => Promise<string>>(),
    logout: vi.fn(),
  },
}))

import { authApi } from '../services/api'
import Login from '../pages/Login'

const Wrapper = ({ children }: { children?: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

afterEach(() => {
  vi.clearAllMocks()
})

// ── Helpers ───────────────────────────────────────────────────────────────────
const fillLoginForm = (username: string, password: string) => {
  fireEvent.change(screen.getByPlaceholderText('admin'), {
    target: { value: username },
  })
  fireEvent.change(screen.getByPlaceholderText('••••••••'), {
    target: { value: password },
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('Login', () => {
  it('renders the sign-in form', () => {
    render(<Login />, { wrapper: Wrapper })
    expect(screen.getByPlaceholderText('admin')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByText(/trafficvision/i)).toBeInTheDocument()
  })

  it('calls authApi.login on submit', async () => {
    ;(authApi.login as ReturnType<typeof vi.fn>).mockResolvedValueOnce('mock-token')

    render(<Login />, { wrapper: Wrapper })
    fillLoginForm('admin', 'admin123')
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledTimes(1)
      expect(authApi.login).toHaveBeenCalledWith('admin', 'admin123')
    })
  })

  it('displays error message on failed login', async () => {
    ;(authApi.login as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('401 Unauthorized')
    )

    render(<Login />, { wrapper: Wrapper })
    fillLoginForm('baduser', 'badpass')
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(
        screen.getByText(/invalid username or password/i)
      ).toBeInTheDocument()
    })
  })

  it('shows loading state while waiting for login', () => {
    ;(authApi.login as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}) // never resolves
    )

    render(<Login />, { wrapper: Wrapper })
    fillLoginForm('admin', 'admin123')
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    const button = screen.getByRole('button', { name: /sign in/i })
    expect(button).toBeDisabled()
    expect(screen.getByText('Signing in...')).toBeInTheDocument()
  })
})