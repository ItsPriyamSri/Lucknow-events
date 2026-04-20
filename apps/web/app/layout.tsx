import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Lucknow Tech Events",
  description: "One place for upcoming tech events in Lucknow.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} font-sans bg-background text-foreground antialiased`}
      >
        <div className="flex h-screen overflow-hidden">
          <aside className="hidden w-64 border-r border-border bg-card md:block flex-shrink-0">
            <Sidebar />
          </aside>
          
          <div className="flex min-w-0 flex-1 flex-col relative w-full">
            {/* Mobile Header */}
            <header className="flex flex-shrink-0 h-14 items-center border-b border-border bg-card px-4 md:hidden">
              <span className="font-bold text-primary tracking-wide">Lucknow Tech Events</span>
            </header>
            <main className="flex-1 overflow-y-auto w-full relative">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
