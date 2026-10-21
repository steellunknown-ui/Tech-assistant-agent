import { NextRequest, NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const room = body.room || "tech-support-session";
    const identity = body.identity || `user-${Math.random().toString(36).substring(2, 9)}`;
    const name = body.name || "Customer";

    const apiKey = process.env.LIVEKIT_API_KEY;
    const apiSecret = process.env.LIVEKIT_API_SECRET;
    const livekitUrl = process.env.LIVEKIT_URL || process.env.NEXT_PUBLIC_LIVEKIT_URL;

    if (!apiKey || !apiSecret || !livekitUrl) {
      return NextResponse.json(
        {
          error: "Missing LiveKit server credentials in environment.",
          details: "Please configure LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL.",
        },
        { status: 500 }
      );
    }

    const at = new AccessToken(apiKey, apiSecret, {
      identity,
      name,
      ttl: "15m",
    });

    at.addGrant({
      roomJoin: true,
      room,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true,
    });

    const token = await at.toJwt();

    return NextResponse.json({
      token,
      url: livekitUrl,
      room,
      identity,
    });
  } catch (error: any) {
    console.error("Failed to generate token:", error);
    return NextResponse.json(
      { error: "Failed to generate token", message: error?.message || String(error) },
      { status: 500 }
    );
  }
}
