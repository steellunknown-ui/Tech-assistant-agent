"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Room, RoomEvent, Track, RemoteTrack, RemoteTrackPublication, RemoteParticipant } from "livekit-client";

type AgentState = "disconnected" | "connecting" | "listening" | "thinking" | "speaking";

export default function VoiceAgentPage() {
  const [agentState, setAgentState] = useState<AgentState>("disconnected");
  const [isConnected, setIsConnected] = useState(false);
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusText, setStatusText] = useState("Ready to connect");

  const roomRef = useRef<Room | null>(null);
  const audioElementsRef = useRef<HTMLAudioElement[]>([]);
  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up audio elements attached during the session
  const cleanupAudio = useCallback(() => {
    audioElementsRef.current.forEach((el) => {
      el.pause();
      el.srcObject = null;
      el.remove();
    });
    audioElementsRef.current = [];
  }, []);

  // Connect to LiveKit Room
  const handleConnect = async () => {
    if (isConnected) {
      await handleDisconnect();
      return;
    }

    try {
      setErrorMessage(null);
      setAgentState("connecting");
      setStatusText("Requesting session token...");

      // 1. Fetch token from Next.js Route Handler
      const res = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room: `support-session-${Math.random().toString(36).substring(2, 7)}`,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.details || errorData.error || "Failed to obtain room token");
      }

      const { token, url } = await res.json();
      setStatusText("Connecting to LiveKit room...");

      // 2. Initialize LiveKit Room instance
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });
      roomRef.current = room;

      // Track subscriptions (Agent's TTS audio stream)
      room.on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            const el = track.attach();
            el.id = `remote-audio-${track.sid}`;
            el.autoplay = true;
            document.body.appendChild(el);
            audioElementsRef.current.push(el);
            el.play().catch(() => {
              // Browser autoplay blocked, try unlocking via LiveKit
              room.startAudio().catch(() => {});
            });
          }
        }
      );

      // Listen for mobile audio playback permission status
      room.on(RoomEvent.AudioPlaybackStatusChanged, () => {
        if (!room.canPlaybackAudio) {
          room.startAudio().catch(() => {});
        }
      });

      // Handle track removal
      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        track.detach().forEach((el) => el.remove());
      });

      // Active speaker detection to track Listening / Thinking / Speaking states
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        if (!roomRef.current) return;

        const localSpeaker = speakers.find((s) => s.isLocal);
        const remoteSpeaker = speakers.find((s) => !s.isLocal);

        if (remoteSpeaker) {
          // Agent is speaking
          if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current);
          setAgentState("speaking");
          setStatusText("Agent is speaking...");
        } else if (localSpeaker) {
          // User is speaking (Agent is listening)
          if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current);
          setAgentState("listening");
          setStatusText("Listening to you...");
        } else {
          // Silence: If we were previously listening, transition briefly to thinking
          setAgentState((prev) => {
            if (prev === "listening") {
              if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current);
              thinkingTimeoutRef.current = setTimeout(() => {
                setAgentState("thinking");
                setStatusText("Agent is thinking...");
              }, 400);
              return prev;
            }
            if (prev === "speaking") {
              setStatusText("Listening for your reply...");
              return "listening";
            }
            return prev;
          });
        }
      });

      // Disconnect event
      room.on(RoomEvent.Disconnected, () => {
        setIsConnected(false);
        setAgentState("disconnected");
        setStatusText("Disconnected");
        cleanupAudio();
      });

      // 3. Connect to room
      await room.connect(url, token);

      // Unlock mobile audio explicitly right inside user click gesture
      try {
        await room.startAudio();
      } catch (audioErr) {
        console.warn("Mobile audio autoplay blocked on connect:", audioErr);
      }

      // 4. Enable local microphone
      await room.localParticipant.setMicrophoneEnabled(true);
      setIsMicEnabled(true);
      setIsConnected(true);
      setAgentState("listening");
      setStatusText("Connected. Agent is ready.");
    } catch (err: any) {
      console.error("Connection error:", err);
      setErrorMessage(err?.message || "Failed to connect to voice room.");
      setAgentState("disconnected");
      setStatusText("Connection error");
      cleanupAudio();
    }
  };

  // Disconnect from room
  const handleDisconnect = async () => {
    if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current);
    if (roomRef.current) {
      await roomRef.current.disconnect();
      roomRef.current = null;
    }
    cleanupAudio();
    setIsConnected(false);
    setAgentState("disconnected");
    setStatusText("Disconnected");
  };

  // Toggle Microphone
  const toggleMic = async () => {
    if (!roomRef.current || !isConnected) return;
    try {
      const nextState = !isMicEnabled;
      await roomRef.current.localParticipant.setMicrophoneEnabled(nextState);
      setIsMicEnabled(nextState);
    } catch (err) {
      console.error("Failed to toggle microphone:", err);
    }
  };

  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
      cleanupAudio();
      if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current);
    };
  }, [cleanupAudio]);

  return (
    <main className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="badge-phase">
          <span className="badge-dot" />
          AI Voice Support
        </div>
        <h1 className="app-title">Technical Support Voice Agent</h1>
        <p className="app-subtitle">
          Real-time intelligent voice assistant for instant technical troubleshooting.
        </p>
      </header>

      {/* Main Glassmorphic Card */}
      <section className={`agent-card state-${agentState}`}>
        {/* Dynamic Voice Orb Visualizer */}
        <div className="orb-container">
          <div className="orb-ring-outer" />
          <div className="orb-ring-pulse" />
          <div className="orb-core">
            <div className="sound-bars">
              <span className="sound-bar" />
              <span className="sound-bar" />
              <span className="sound-bar" />
              <span className="sound-bar" />
              <span className="sound-bar" />
            </div>
          </div>
        </div>

        {/* State Indicator Pill */}
        <div id="agent-state-pill" className="state-pill">
          <span className="state-pill-dot" />
          <span style={{ textTransform: "capitalize" }}>
            {agentState === "disconnected" ? "Idle / Offline" : agentState}
          </span>
        </div>

        {/* Status text */}
        <p id="room-status" className="diag-message">
          {statusText}
        </p>

        {/* Error Notification */}
        {errorMessage && (
          <div id="error-banner" className="diag-message error">
            {errorMessage}
          </div>
        )}

        {/* Interactive Controls */}
        <div className="controls-group">
          {/* Connect / Disconnect Button */}
          <button
            id="connect-btn"
            className={`btn-primary ${isConnected ? "btn-disconnect" : ""}`}
            onClick={handleConnect}
            disabled={agentState === "connecting"}
          >
            {agentState === "connecting" ? (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 1s linear infinite" }}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                Connecting...
              </>
            ) : isConnected ? (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                  <line x1="12" y1="2" x2="12" y2="12" />
                </svg>
                End Call
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                </svg>
                Start Voice Support
              </>
            )}
          </button>

          {/* Microphone Mute/Unmute Toggle */}
          <button
            id="mic-btn"
            className={`btn-mic ${!isMicEnabled ? "muted" : ""}`}
            onClick={toggleMic}
            disabled={!isConnected}
            title={isMicEnabled ? "Mute Microphone" : "Unmute Microphone"}
            aria-label={isMicEnabled ? "Mute Microphone" : "Unmute Microphone"}
          >
            {isMicEnabled ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            ) : (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="2" y1="2" x2="22" y2="22" />
                <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2" />
                <path d="M5 10v2a7 7 0 0 0 12 5" />
                <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33" />
                <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            )}
          </button>
        </div>
      </section>
    </main>
  );
}
