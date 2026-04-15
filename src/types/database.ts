export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          phone: string
          name: string
          created_at: string
        }
        Insert: {
          id?: string
          phone: string
          name: string
          created_at?: string
        }
        Update: {
          id?: string
          phone?: string
          name?: string
          created_at?: string
        }
      }
      pets: {
        Row: {
          id: string
          user_id: string
          name: string
          type: string
          breed: string | null
          age: number | null
          photo_url: string | null
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          name: string
          type: string
          breed?: string | null
          age?: number | null
          photo_url?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          name?: string
          type?: string
          breed?: string | null
          age?: number | null
          photo_url?: string | null
          created_at?: string
        }
      }
      transport_orders: {
        Row: {
          id: string
          pet_id: string
          tracking_number: string
          status: string
          current_location: Json | null
          estimated_arrival: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          pet_id: string
          tracking_number: string
          status?: string
          current_location?: Json | null
          estimated_arrival?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          pet_id?: string
          tracking_number?: string
          status?: string
          current_location?: Json | null
          estimated_arrival?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      tracking_updates: {
        Row: {
          id: string
          order_id: string
          status: string
          location: string | null
          latitude: number | null
          longitude: number | null
          description: string | null
          created_at: string
        }
        Insert: {
          id?: string
          order_id: string
          status: string
          location?: string | null
          latitude?: number | null
          longitude?: number | null
          description?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          order_id?: string
          status?: string
          location?: string | null
          latitude?: number | null
          longitude?: number | null
          description?: string | null
          created_at?: string
        }
      }
    }
  }
}
