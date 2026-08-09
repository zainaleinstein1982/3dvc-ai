import { Room, RoomEvent, Track, RemoteParticipant } from 'livekit-client';

export class SFUTransport {
  private room: Room;
  public localId: string = '';
  public onRemoteStream: (id: string, stream: MediaStream) => void = () => {};
  public onRemoteTrackingData: (id: string, data: any) => void = () => {};
  public onParticipantJoined: (id: string) => void = () => {};
  public onParticipantLeft: (id: string) => void = () => {};

  constructor() {
    this.room = new Room();
    this.setupEvents();
  }

  private setupEvents() {
    this.room.on(RoomEvent.ParticipantConnected, (p: RemoteParticipant) => this.onParticipantJoined(p.identity));
    this.room.on(RoomEvent.ParticipantDisconnected, (p: RemoteParticipant) => this.onParticipantLeft(p.identity));
    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio && participant?.identity) {
        const stream = new MediaStream([track.mediaStreamTrack]);
        this.onRemoteStream(participant.identity, stream);
      }
    });
    this.room.on(RoomEvent.DataReceived, (payload, participant) => {
      if (participant?.identity) {
        this.onRemoteTrackingData(participant.identity, JSON.parse(new TextDecoder().decode(payload)));
      }
    });
  }

  async connect(roomId: string, userId: string) {
    const API_URL = 'https://3dvc-ai-production.up.railway.app';
    
    // Cek beberapa kemungkinan key token di localStorage agar tidak null
    const tokenStr = localStorage.getItem('token') || 
                     localStorage.getItem('access_token') || 
                     localStorage.getItem('authToken') || '';

    const res = await fetch(`${API_URL}/api/sfu/token?room=${roomId}`, {
      headers: { 
        'Authorization': `Bearer ${tokenStr}` 
      }
    });

    if (!res.ok) {
      throw new Error(`Gagal mengambil token SFU: Status ${res.status}`);
    }

    const data = await res.json();
    if (!data || !data.token || !data.url) {
      throw new Error('Format token SFU dari backend tidak valid');
    }

    await this.room.connect(data.url, data.token);
    this.localId = this.room.localParticipant.identity;
    this.room.remoteParticipants.forEach(p => this.onParticipantJoined(p.identity));
  }

  async publishTrack(track: MediaStreamTrack) {
    await this.room.localParticipant.publishTrack(track);
  }

  sendData(data: any) {
    this.room.localParticipant.publishData(new TextEncoder().encode(JSON.stringify(data)), { reliable: true });
  }

  disconnect() { this.room.disconnect(); }
}