import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SmartPlan AI v3.0",
  description: "Automated Industrial Park Planning Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="antialiased bg-gray-950">
        {children}
      </body>
    </html>
  );
}
