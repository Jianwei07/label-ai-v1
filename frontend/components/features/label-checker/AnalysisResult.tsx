"use client";

import { LabelAnalysisResult } from "@/lib/types";
import { HighlightOverlay } from "./HighlightOverlay";
import { Loader2, Image as ImageIcon } from "lucide-react";
import Image from "next/image"; // Make sure this is imported

interface AnalysisResultDisplayProps {
  imageUrl: string | null;
  result: LabelAnalysisResult | null;
  isLoading: boolean;
}

export function AnalysisResultDisplay({
  imageUrl,
  result,
  isLoading,
}: AnalysisResultDisplayProps) {
  return (
    <div className="relative w-full min-h-[400px] flex items-center justify-center border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-100/50 dark:bg-gray-800/20 overflow-hidden">
      {isLoading && (
        <div className="flex flex-col items-center text-gray-500 dark:text-gray-400 animate-pulse">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="mt-2">Processing...</p>
        </div>
      )}

      {!isLoading && !imageUrl && (
        <div className="text-center text-gray-500 dark:text-gray-400">
          <ImageIcon className="mx-auto h-12 w-12" />
          <p className="mt-2 font-medium">Awaiting Image</p>
          <p className="text-sm">
            Your uploaded label image will be displayed here.
          </p>
        </div>
      )}

      {/* This is the corrected section */}
      {imageUrl && (
        // This parent div MUST have `position: relative`. The image will fill this container.
        // It's also important that this div has a defined size, which it gets from its parent flex container.
        <div className="relative w-full h-full max-h-[600px]">
          <Image
            id="label-image"
            src={imageUrl}
            alt="Uploaded Label"
            fill // This makes the image `position: absolute` and fill the parent div
            className="object-contain" // This scales the image correctly within its box
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw" // Helps Next.js optimize image loading
          />
          {result && (
            <HighlightOverlay
              highlights={result.highlights}
              imageElementId="label-image"
            />
          )}
        </div>
      )}

      {result && !isLoading && (
        <div className="absolute top-2 right-2 p-2 bg-white/80 dark:bg-black/70 backdrop-blur-sm rounded-md shadow-lg text-xs border border-gray-200 dark:border-gray-700">
          <h4 className="font-bold mb-1">Summary</h4>
          <p>
            <strong>Status:</strong>
            <span
              className={`font-semibold ${
                result.overall_status.startsWith("fail")
                  ? "text-red-500"
                  : "text-green-500"
              }`}
            >
              {result.overall_status.replace("_", " ").toUpperCase()}
            </span>
          </p>
          <p>
            <strong>Matches:</strong> {result.summary.matches || 0}
          </p>
          <p>
            <strong>Mismatches:</strong>{" "}
            {result.summary.mismatches_or_errors_in_rules || 0}
          </p>
        </div>
      )}
    </div>
  );
}
