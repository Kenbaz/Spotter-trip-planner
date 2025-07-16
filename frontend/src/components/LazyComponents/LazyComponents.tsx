import { lazy, Suspense } from "react";
// import { LoadingSpinner } from "../UI/LoadingSpinner";

const DashboardPage = lazy(() => import("../../pages/Dashboard"));
const TripsPage = lazy(() => import("../../pages/TripsPage"));
const TripDetailPage = lazy(() => import("../../pages/TripsDetailsPage"));


const LazyLoadedComponent = ({ children }: { children: React.ReactNode }) => {
    return (
        <Suspense>
            {children}
        </Suspense>
    )
};

export const LazyLoadedDashboardPage = () => (
    <LazyLoadedComponent>
        <DashboardPage />
    </LazyLoadedComponent>
);

export const LazyLoadedTripsPage = () => (
    <LazyLoadedComponent>
        <TripsPage />
    </LazyLoadedComponent>
);

export const LazyLoadedTripDetailPage = () => (
    <LazyLoadedComponent>
        <TripDetailPage />
    </LazyLoadedComponent>
);