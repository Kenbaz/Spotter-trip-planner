import React, { useState, useEffect, useRef, useCallback } from "react";
import { MapPin, CheckCircle, AlertCircle, Loader2, CircleX } from "lucide-react";
import { useGeocodeMutation } from "../../hooks/useTripQueries";


interface AddressSuggestion {
    id: string;
    display_name: string;
    formatted_address: string;
    latitude: number;
    longitude: number;
    confidence: number;
    locality?: string;
    region?: string;
    country?: string;
}

interface AddressAutocompleteProps {
  value: string;
  onChange: (address: string) => void;
  onCoordinatesChange: (
    lat: number,
    lng: number,
    formattedAddress: string
  ) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  autoFocus?: boolean;
  debounceMs?: number;
}


export function AddressAutocomplete({ 
    value, 
    onChange, 
    onCoordinatesChange, 
    placeholder = "Enter address...", 
    label, 
    error, 
    disabled = false, 
    required = false, 
    className = "", 
    autoFocus = false, 
    debounceMs = 300
}: AddressAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isGeocoded, setIsGeocoded] = useState(false);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>(null);

  const geocodeMutation = useGeocodeMutation();

  // Clear geocode state when value changes
  useEffect(() => {
    setIsGeocoded(false);
    setGeocodeError(null);
  }, [value]);

  const debouncedSearch = useCallback(
    (searchTerm: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(async () => {
        if (searchTerm.trim().length < 3) {
          setSuggestions([]);
          setIsOpen(false);
          return;
        }

        setIsSearching(true);
        try {
          // Call geocode API
          const result = await geocodeMutation.mutateAsync(searchTerm.trim());

          if (result.success) {
            // Convert API response to suggestions
            const suggestion: AddressSuggestion = {
              id: `${result.latitude}-${result.longitude}`,
              display_name: result.formatted_address || searchTerm,
              formatted_address: result.formatted_address || searchTerm,
              latitude: result.latitude!,
              longitude: result.longitude!,
              confidence: result.confidence || 1,
              locality: result.locality,
              region: result.region,
              country: result.country,
            };

            setSuggestions([suggestion]);
            setIsOpen(true);
            setSelectedIndex(-1);
          } else {
            setSuggestions([]);
            setIsOpen(false);
          }
        } catch (error) {
          console.error("Address search error:", error);
          setSuggestions([]);
          setIsOpen(false);
        } finally {
          setIsSearching(false);
        }
      }, debounceMs);
    },
    [debounceMs, geocodeMutation]
  );

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    if (newValue.trim()) {
      debouncedSearch(newValue);
    } else {
      setSuggestions([]);
      setIsOpen(false);
    }
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion: AddressSuggestion) => {
    onChange(suggestion.formatted_address);
    onCoordinatesChange(
      suggestion.latitude,
      suggestion.longitude,
      suggestion.formatted_address
    );
    setIsGeocoded(true);
    setGeocodeError(null);
    setSuggestions([]);
    setIsOpen(false);
    setSelectedIndex(-1);
    inputRef.current?.blur();
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === "Enter" && value.trim() && !isGeocoded) {
        e.preventDefault();
        handleDirectGeocode();
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSuggestionSelect(suggestions[selectedIndex]);
        } else if (suggestions.length === 1) {
          handleSuggestionSelect(suggestions[0]);
        } else {
          handleDirectGeocode();
        }
        break;
      case "Escape":
        setIsOpen(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  // Direct geocode when user types and presses Enter
  const handleDirectGeocode = async () => {
    if (!value.trim() || isSearching) return;

    setIsSearching(true);
    setGeocodeError(null);

    try {
      const result = await geocodeMutation.mutateAsync(value.trim());

      if (result.success) {
        onCoordinatesChange(
          result.latitude!,
          result.longitude!,
          result.formatted_address || value
        );
        setIsGeocoded(true);
        onChange(result.formatted_address || value);
      } else {
        setGeocodeError(result.error || "Address not found");
      }
    } catch (error) {
      console.error("Failed to find address", error);
      setGeocodeError("Failed to find address");
    } finally {
      setIsSearching(false);
    }
  };

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Auto-geocode when user stops typing and field loses focus
  const handleBlur = () => {
    setTimeout(() => {
      if (value.trim() && !isGeocoded && suggestions.length === 0) {
        handleDirectGeocode();
      }
    }, 200);
  };

  // Clear address
  const handleClear = () => {
    onChange("");
    setIsGeocoded(false);
    setGeocodeError(null);
    setSuggestions([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const getStatusIcon = () => {
    if (isSearching) {
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    }
    if (isGeocoded) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    if (geocodeError) {
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
    return <MapPin className="w-4 h-4 text-gray-400" />;
    };
    

    return (
      <div className={`relative ${className}`}>
        {label && (
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}

        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder={placeholder}
            disabled={disabled}
            autoFocus={autoFocus}
            className={`
                w-full px-3 py-3 pl-10 pr-10 border rounded-md
                bg-[#FAFAFA] focus:ring-2 focus:ring-blue-700 text-gray-900 focus:outline-none
                disabled:bg-gray-50 disabled:text-gray-500
                ${error || geocodeError ? "ring-2 ring-red-500" : "border-gray-300"}
                ${isGeocoded ? "bg-green-50 border-green-300" : ""}
              `}
          />

          {/* Status Icon */}
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {getStatusIcon()}
          </div>

          {/* Clear Button */}
          {value && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-700"
            >
              <CircleX className="w-4 h-4 md:h-5 md:w-5 text-gray-500 hover:text-gray-800 relative right-[1.3rem] md:right-[2.8rem]" />
            </button>
          )}
        </div>

        {/* Suggestions Dropdown */}
        {isOpen && suggestions.length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto"
          >
            {suggestions.map((suggestion, index) => (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => handleSuggestionSelect(suggestion)}
                className={`
                    w-full text-left px-4 py-3 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none
                    border-b border-gray-100 last:border-b-0
                    ${index === selectedIndex ? "bg-blue-50" : ""}
                  `}
              >
                <div className="flex items-start space-x-3">
                  <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {suggestion.display_name}
                    </p>
                    {suggestion.locality && suggestion.region && (
                      <p className="text-xs text-gray-500 mt-1">
                        {suggestion.locality}, {suggestion.region}
                      </p>
                    )}
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-gray-400">
                        Confidence: {Math.round(suggestion.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Error Message */}
        {(error || geocodeError) && (
          <p className="mt-1 text-sm text-red-600">{error || geocodeError}</p>
        )}
      </div>
    );
}