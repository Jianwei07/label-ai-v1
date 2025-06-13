"use client";

import { useState } from "react";
import { LabelAnalysisResult, HighlightedElement } from "@/lib/types";
import { HighlightOverlay } from "./HighlightOverlay";
import { Loader2, ImageIcon, AlertTriangle, CheckCircle } from "lucide-react";
import Image from "next/image"; // Import the Next.js Image component

interface AnalysisResultDisplayProps {
  initialImageUrl: string | null; // The original uploaded image for preview
  result: LabelAnalysisResult | null;
  isLoading: boolean;
}

export function AnalysisResultDisplay({
  initialImageUrl,
  result,
  isLoading,
}: AnalysisResultDisplayProps) {
  const [focusedHighlight, setFocusedHighlight] =
    useState<HighlightedElement | null>(null);

  // Determine which image URL to show
  const displayImageUrl = result?.processed_image_url || initialImageUrl;

  const faults = result?.highlights.filter((h) => h.status === "wrong") || [];
  const successes =
    result?.highlights.filter((h) => h.status === "correct") || [];

  return (
    <div className="space-y-4">
      {/* Image Display Area */}
      <div className="w-full min-h-[400px] flex items-center justify-center border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-100/50 dark:bg-gray-800/20 overflow-hidden">
        {isLoading && (
          <div className="flex flex-col items-center text-gray-500 dark:text-gray-400 animate-pulse">
            <Loader2 className="h-8 w-8 animate-spin" />
            <p className="mt-2">Generating Report...</p>
          </div>
        )}
        {!isLoading && !displayImageUrl && (
          <div className="text-center text-gray-500 dark:text-gray-400">
            <ImageIcon className="mx-auto h-12 w-12" />
            <p className="mt-2 font-medium">
              Analysis results will appear here.
            </p>
          </div>
        )}
        {displayImageUrl && (
          // --- FIX IS HERE ---
          // This parent div MUST have `position: relative` for the `fill` prop to work correctly.
          // It also needs a defined size, which it gets from the parent container.
          // The max-h-[70vh] sets the container's max height.
          <div className="relative w-full h-full max-h-[70vh] aspect-[3/4]">
            <Image
              id="label-image"
              src={displayImageUrl}
              alt="Analyzed Label"
              fill // The fill prop makes the image expand to the parent div's dimensions.
              className="object-contain" // This ensures the image scales correctly.
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw" // Helps Next.js optimize image loading
            />
            <HighlightOverlay
              highlights={result?.highlights || []}
              imageElementId="label-image"
              focusedHighlight={focusedHighlight}
            />
          </div>
        )}
      </div>

      {/* Interactive Faults List */}
      {result && faults.length > 0 && (
        <div>
          <h3 className="font-bold text-lg mb-2 flex items-center gap-2 text-red-600">
            <AlertTriangle />
            Detected Faults ({faults.length})
          </h3>
          <ul className="space-y-2 max-h-48 overflow-y-auto p-2 border rounded-md">
            {faults.map((fault, index) => (
              <li
                key={index}
                className="p-2 rounded-md hover:bg-red-100/50 dark:hover:bg-red-900/20 cursor-pointer"
                onMouseEnter={() => setFocusedHighlight(fault)}
                onMouseLeave={() => setFocusedHighlight(null)}
              >
                <p className="font-semibold text-sm">{fault.message}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Expected: {fault.expected_value || "N/A"} | Found:{" "}
                  {fault.found_value || "N/A"}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
      {/* List of Correct Items (Optional) */}
      {result && successes.length > 0 && (
        <div>
          <h3 className="font-bold text-lg mb-2 flex items-center gap-2 text-green-600">
            <CheckCircle />
            Correct Items ({successes.length})
          </h3>
        </div>
      )}
    </div>
  );
}
