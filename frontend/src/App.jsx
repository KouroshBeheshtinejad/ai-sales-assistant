import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { ErrorBoundary, NotFound, PublicLayout } from './components/Layout'
import { Loading, ToastProvider } from './components/ui'
import { AuthProvider, RequireAuth } from './lib/auth'
import { I18nProvider } from './lib/i18n'
import AuthPage from './pages/Auth'
import Landing from './pages/Landing'
import StoreHome from './pages/StoreHome'
import StoreShell from './pages/StoreShell'
import ProductPage from './pages/ProductPage'
import Track from './pages/Track'

// The seller panel is only needed by store owners: keep it out of the storefront bundle.
const SellerLayout = lazy(() => import('./pages/seller/SellerLayout'))
const Overview = lazy(() => import('./pages/seller/Overview'))
const Orders = lazy(() => import('./pages/seller/Orders'))
const OrderDetail = lazy(() => import('./pages/seller/OrderDetail'))
const Conversations = lazy(() => import('./pages/seller/Conversations'))
const ConversationDetail = lazy(() => import('./pages/seller/Conversations').then((m) => ({ default: m.ConversationDetail })))
const Products = lazy(() => import('./pages/seller/Products'))
const Knowledge = lazy(() => import('./pages/seller/Knowledge'))

// Paths mirror the routes FastAPI serves index.html for (see app/main.py).
export default function App() {
  return (
    <I18nProvider>
      <ToastProvider>
        <AuthProvider>
          <ErrorBoundary>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route element={<PublicLayout />}>
                  <Route index element={<Landing />} />
                  <Route path="landing" element={<Landing />} />
                  <Route path="login" element={<AuthPage initial="login" />} />
                  <Route path="register" element={<AuthPage initial="register" />} />
                  <Route path="track" element={<Track />} />
                  <Route path="*" element={<NotFound />} />
                </Route>

                <Route path="store/:id" element={<StoreShell />}>
                  <Route index element={<StoreHome />} />
                  <Route path="product/:productId" element={<ProductPage />} />
                </Route>

                <Route path="seller" element={<RequireAuth><SellerLayout /></RequireAuth>}>
                  <Route index element={<Overview />} />
                  <Route path="orders" element={<Orders />} />
                  <Route path="order/:orderId" element={<OrderDetail />} />
                  <Route path="conversations" element={<Conversations />} />
                  <Route path="conversation/:conversationId" element={<ConversationDetail />} />
                  <Route path="products" element={<Products />} />
                  <Route path="knowledge" element={<Knowledge />} />
                </Route>
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </AuthProvider>
      </ToastProvider>
    </I18nProvider>
  )
}
