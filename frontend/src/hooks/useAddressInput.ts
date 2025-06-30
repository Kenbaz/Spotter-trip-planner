import { useState, useCallback } from "react";


interface AddressData {
    address: string;
    latitude: number | null;
    longitude: number | null;
    isGeocoded: boolean;
}


export function useAddressInput(initialAddress = "") {
    const [addressData, setAddressData] = useState<AddressData>({
        address: initialAddress,
        latitude: null,
        longitude: null,
        isGeocoded: false,
    });

    const handleAddressChange = useCallback((address: string) => {
        setAddressData(prev => ({
            ...prev,
            address,
            isGeocoded: false,
        }));
    }, [])

    const handleCoordinatesChange = useCallback((
        latitude: number,
        longitude: number,
        formattedAddress: string
    ) => {
        setAddressData({
            address: formattedAddress,
            latitude,
            longitude,
            isGeocoded: true,
        });
    }, []);

    const resetAddress = useCallback(() => {
        setAddressData({
            address: "",
            latitude: null,
            longitude: null,
            isGeocoded: false,
        });
    }, []);


    return {
        addressData,
        handleAddressChange,
        handleCoordinatesChange,
        resetAddress,
        isValid: addressData.isGeocoded && addressData.latitude !== null && addressData.longitude !== null,
    };
};