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
    const res = await fetch(`http://localhost:8000/api/sfu/token?room=${roomId}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } // Simplified for script
    });
    const { token, url } = await res.json();
    await this.room.connect(url, token);
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