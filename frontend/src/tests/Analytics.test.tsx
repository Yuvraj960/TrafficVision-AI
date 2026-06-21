import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

const MOCK_SUMMARY = {
  total_violations: 87,
  by_type: {
    helmet: 30,
    triple_riding: 20,
    wrong_side: 18,
    stop_line: 12,
    overloading: 7,
    no_violation: 0,
  },
}

const MOCK_STATUS_BREAKDOWN = {
  data: Array.from({ length: 87 }, (_, i) => ({
    id: String(i),
    violation_type: 'helmet',
    plate_number: 'test',
    timestamp: new Date().toISOString(),
    status: i < 10 ? 'pending' : i < 50 ? 'approved' : 'rejected',
    image_url: 'http://test/img.jpg',
    confidence_score: 0.9,
  })),
  meta: { total: 87, page: 1, limit: 200 },
}

vi.mock('../services/api', () => ({
  analyticsApi: {
    summary: vi.fn<() => Promise<typeof MOCK_SUMMARY>>(),
  },
  violationsApi: {
    list: vi.fn<() => Promise<typeof MOCK_STATUS_BREAKDOWN>>(),
  },
}))

import Analytics from '../pages/Analytics'
import { analyticsApi, violationsApi } from '../services/api'

const Wrapper = ({ children }: { children?: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

afterEach(() => vi.clearAllMocks())

describe('Analytics', () => {
  it('renders the analytics page title', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_SUMMARY)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_STATUS_BREAKDOWN)

    render(<Analytics />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('Analytics')).toBeInTheDocument()
    })
  })

  it('shows total violation count', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_SUMMARY)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_STATUS_BREAKDOWN)

    render(<Analytics />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('87')).toBeInTheDocument()
    })
  })

  it('renders time-range selector buttons', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_SUMMARY)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_STATUS_BREAKDOWN)

    render(<Analytics />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('Today')).toBeInTheDocument()
      expect(screen.getByText('Last 7 Days')).toBeInTheDocument()
      expect(screen.getByText('Last 30 Days')).toBeInTheDocument()
      expect(screen.getByText('All Time')).toBeInTheDocument()
    })
  })

  it('re-fetches data when time range is changed', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(MOCK_SUMMARY)
      .mockResolvedValueOnce({ ...MOCK_SUMMARY, total_violations: 200 })
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_STATUS_BREAKDOWN)

    render(<Analytics />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('87')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Last 30 Days'))

    await waitFor(() => {
      expect(analyticsApi.summary).toHaveBeenCalledTimes(2)
    })
  })

  it('shows violation type labels in chart', async () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_SUMMARY)
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_STATUS_BREAKDOWN)

    render(<Analytics />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('Helmet')).toBeInTheDocument()
      expect(screen.getByText('Triple Riding')).toBeInTheDocument()
      expect(screen.getByText('Wrong Side')).toBeInTheDocument()
    })
  })

  it('shows loading state while fetching', () => {
    ;(analyticsApi.summary as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    )
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Analytics />, { wrapper: Wrapper })

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })
})