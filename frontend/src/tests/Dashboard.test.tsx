import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

const MOCK_LIST_RESPONSE = {
  data: [
    {
      id: '11111111-1111-1111-1111-111111111111',
      violation_type: 'helmet',
      plate_number: 'MH 12 AB 1234',
      timestamp: new Date().toISOString(),
      status: 'pending',
      image_url: 'http://test/img.jpg',
      confidence_score: 0.87,
    },
  ],
  meta: { total: 1, page: 1, limit: 20 },
}

const MOCK_ANALYTICS = {
  total_violations: 42,
  by_type: { helmet: 15, triple_riding: 12, wrong_side: 8, stop_line: 4, overloading: 3 },
}

vi.mock('../services/api', () => ({
  analyticsApi: { summary: vi.fn<() => Promise<typeof MOCK_ANALYTICS>>() },
  violationsApi: {
    list: vi.fn<() => Promise<typeof MOCK_LIST_RESPONSE>>(),
    get: vi.fn(),
    updateStatus: vi.fn(),
  },
}))

import Dashboard from '../pages/Dashboard'
import { analyticsApi, violationsApi } from '../services/api'

const Wrapper = ({ children }: { children?: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

afterEach(() => vi.clearAllMocks())

describe('Dashboard', () => {
  it('renders stat cards after data loads', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_ANALYTICS)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Dashboard />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText(/total violations/i)).toBeInTheDocument()
    })
    // Shows total count from analytics
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument()
    })
  })

  it('calls analyticsApi.summary and violationsApi.list on mount', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_ANALYTICS)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Dashboard />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(analyticsApi.summary).toHaveBeenCalledTimes(1)
      expect(violationsApi.list).toHaveBeenCalledTimes(1)
    })
  })

  it('renders a violations table row', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_ANALYTICS)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Dashboard />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('helmet')).toBeInTheDocument()
    })
    expect(screen.getByText('MH 12 AB 1234')).toBeInTheDocument()
  })

  it('shows loading spinner while fetching', () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    )
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Dashboard />, { wrapper: Wrapper })

    // Spinner should be visible while loading
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })
})