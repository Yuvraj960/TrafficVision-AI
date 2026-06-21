import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

const MOCK_DATA: import('../services/api').ViolationListItem[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    violation_type: 'helmet',
    plate_number: 'MH 12 AB 1234',
    timestamp: new Date().toISOString(),
    status: 'pending',
    image_url: 'http://test/img.jpg',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    violation_type: 'triple_riding',
    plate_number: 'DL 01 CD 5678',
    timestamp: new Date().toISOString(),
    status: 'approved',
    image_url: 'http://test/img2.jpg',
  },
]

const MOCK_DETAIL: import('../services/api').ViolationDetailItem = {
  id: '11111111-1111-1111-1111-111111111111',
  violation_type: 'helmet',
  vehicle_type: 'motorcycle',
  plate_number: 'MH 12 AB 1234',
  confidence_score: 0.87,
  status: 'pending',
  image_url: 'http://test/img.jpg',
  plate_image_url: null,
  camera_id: null,
  job_id: null,
  reviewed_by: null,
  reviewed_at: null,
  timestamp: new Date().toISOString(),
  bounding_boxes: {
    vehicles: [{ x: 450, y: 180, w: 130, h: 170, label: 'motorcycle' }],
    helmets: [],
    violations: [{ x: 490, y: 130, w: 40, h: 40, label: 'no_helmet' }],
  },
}

const MOCK_LIST_RESPONSE: import('../services/api').ViolationListResponse = {
  data: MOCK_DATA,
  meta: { total: 2, page: 1, limit: 20 },
}

vi.mock('../services/api', () => ({
  violationsApi: {
    list: vi.fn<() => Promise<typeof MOCK_LIST_RESPONSE>>(),
    get: vi.fn<() => Promise<typeof MOCK_DETAIL>>(),
    updateStatus: vi.fn(),
  },
}))

import Violations from '../pages/Violations'
import { violationsApi } from '../services/api'

const Wrapper = ({ children }: { children?: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

afterEach(() => vi.clearAllMocks())

describe('Violations', () => {
  it('renders the page title and table', async () => {
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Violations />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('Violation Explorer')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('helmet')).toBeInTheDocument()
    })
  })

  it('shows plate numbers in table', async () => {
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Violations />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('MH 12 AB 1234')).toBeInTheDocument()
    })
  })

  it('shows status badge per row', async () => {
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)

    render(<Violations />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getAllByText('pending')).toHaveLength(1)
    })
    await waitFor(() => {
      expect(screen.getAllByText('approved')).toHaveLength(1)
    })
  })

  it('calls updateStatus on approve click', async () => {
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockResolvedValueOnce(MOCK_LIST_RESPONSE)
    ;(violationsApi.updateStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(undefined)

    render(<Violations />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('helmet')).toBeInTheDocument()
    })

    const approveBtns = screen.getAllByRole('button', { name: /approve/i })
    fireEvent.click(approveBtns[0])

    await waitFor(() => {
      expect(violationsApi.updateStatus).toHaveBeenCalledWith(
        expect.any(String),
        { status: 'approved' }
      )
    })
  })

  it('shows loading spinner initially', () => {
    ;(violationsApi.list as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    )

    render(<Violations />, { wrapper: Wrapper })

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })
})