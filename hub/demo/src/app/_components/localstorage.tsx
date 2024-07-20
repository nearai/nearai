import {useEffect, useState} from "react";

export const useLocalStorage = (key) => {
    const [storedValue, setStoredValue] = useState(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem(key);
        }
        return null;
    });

    useEffect(() => {
        const handleStorageChange = () => {
            if (typeof window !== 'undefined') {
                setStoredValue(localStorage.getItem(key));
            }
        };

        window.addEventListener('storage', handleStorageChange);

        return () => {
            window.removeEventListener('storage', handleStorageChange);
        };
    }, [key]);

    const setValue = (value) => {
        if (typeof window !== 'undefined') {
            localStorage.setItem(key, value);
            setStoredValue(value);
        }
    };

    return [storedValue, setValue];
};