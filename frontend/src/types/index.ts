export interface Violation {
  id: string;
  camera_id: string;
  job_id: string;
  violation_type: string;
  vehicle_type: string | null;
  plate_number: string | null;
  confidence_score: number;
  status: 'pending' | 'approved' | 'rejected';
  image_url: string;
  plate_image_url: string | null;
  timestamp: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface Camera {
  id: string;
  name: string;
  location_lat: number | null;
  location_lng: number | null;
  rtsp_url: string | null;
  status: string;
  created_at: string;
}

export interface User {
  id: string;
  username: string;
  role: 'officer' | 'admin';
  created_at: string;
}
