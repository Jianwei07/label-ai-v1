"use client";

import { useState } from "react";
import { LabelAnalysisResult } from "@/lib/types";
import { submitLabelForAnalysis } from "@/lib/api";
import { toast } from "sonner";
import { Toaster } from "../components/ui/sonner";

// Import feature components
import { ImageUploader } from "../components/features/label-checker/ImageUploader";
import { RulesUploader } from "../components/features/label-checker/RulesUploader";
import { AnalysisResultDisplay } from "../components/features/label-checker/AnalysisResult";

// Import UI Primitives
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Terminal } from "lucide-react";

export default function Home() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [rulesFile, setRulesFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  // State for the API call
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] =
    useState<LabelAnalysisResult | null>(null);

  const handleImageUpload = (file: File) => {
    setImageFile(file);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(URL.createObjectURL(file));
    setAnalysisResult(null); // Clear previous results
  };

  const handleRulesUpload = (file: File) => {
    setRulesFile(file);
    setAnalysisResult(null); // Clear previous results
  };

  const handleImageRemove = () => {
    setImageFile(null);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(null);
  };

  const handleRulesRemove = () => {
    setRulesFile(null);
  };

  const handleSubmit = async () => {
    if (!imageFile || !rulesFile) {
      setError("Please provide both a label image and a rules document.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const result = await submitLabelForAnalysis(imageFile, rulesFile, 50);
      setAnalysisResult(result);
      toast.success("Analysis Complete", {
        description: `Overall status: ${result.overall_status
          .replace("_", " ")
          .toUpperCase()}`,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "An unknown error occurred.";
      setError(errorMessage);
      toast.error("Analysis Failed", {
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 sm:p-8 md:p-12 bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-4xl space-y-8">
        <header className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
            AI Regulatory Label Checker
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-300">
            Upload your label and rules document to get instant, precise
            compliance feedback.
          </p>
        </header>

        {/* --- UPDATED: Single-column layout --- */}
        <div className="flex flex-col gap-8">
          {/* Step 1: Upload */}
          <Card>
            <CardHeader>
              <CardTitle>Step 1: Upload Your Files</CardTitle>
              <CardDescription>
                Provide the label image and the rules document.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ImageUploader
                onFileSelect={handleImageUpload}
                currentImageUrl={imageUrl}
                onFileRemove={handleImageRemove}
              />
              <RulesUploader
                onFileSelect={handleRulesUpload}
                currentFile={rulesFile}
                onFileRemove={handleRulesRemove}
              />
            </CardContent>
          </Card>

          <div className="flex justify-center">
            <Button
              onClick={handleSubmit}
              disabled={isLoading || !imageFile || !rulesFile}
              size="lg"
            >
              {isLoading ? "Analyzing..." : "Analyze Label"}
            </Button>
          </div>

          {/* Step 2: Results - This section only shows up after an analysis is attempted */}
          {(isLoading || analysisResult || error) && (
            <Card>
              <CardHeader>
                <CardTitle>Step 2: Analysis Results</CardTitle>
                <CardDescription>
                  Review the highlighted faults and successes on your label.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {error && (
                  <Alert variant="destructive">
                    <Terminal className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <AnalysisResultDisplay
                  // We pass BOTH the original blob URL (for instant preview)
                  // AND the final result object which contains the processed URL
                  initialImageUrl={imageUrl}
                  result={analysisResult}
                  isLoading={isLoading}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
      <Toaster />
    </main>
  );
}
