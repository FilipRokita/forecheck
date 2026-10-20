import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forecheck: how far can you trust a weather forecast?",
  description:
    "Weather models ICON, ECMWF and GFS scored against IMGW station measurements in Poland, by station, quantity and days ahead.",
};

export const viewport: Viewport = { themeColor: "#0b0c0e" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
