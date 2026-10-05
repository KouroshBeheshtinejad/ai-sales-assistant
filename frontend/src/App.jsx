import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary, NotFound, PublicLayout } from './components/Layout'
import { Loading, ToastProvider } from './components/ui'
import { AuthProvider, RequireAuth } from './lib/auth'
import { RequireRoles } from './lib/auth'
import { I18nProvider } from './lib/i18n'
import AuthPage from './pages/Auth'
import Landing from './pages/Landing'
import StoreHome from './pages/StoreHome'
import StoreShell from './pages/StoreShell'
import ProductPage from './pages/ProductPage'
import Track from './pages/Track'
import PaymentResult from './pages/PaymentResult'
import ApiDocs from './pages/ApiDocs'
const About = lazy(() => import('./pages/About'))
const StoreDirectory = lazy(() => import('./pages/StoreDirectory'))

// The seller panel is only needed by store owners: keep it out of the storefront bundle.
const SellerLayout = lazy(() => import('./pages/seller/SellerLayout'))
const RequireStorePermission = lazy(() => import('./pages/seller/SellerLayout').then((module) => ({ default: module.RequireStorePermission })))
const Overview = lazy(() => import('./pages/seller/Overview'))
const Orders = lazy(() => import('./pages/seller/Orders'))
const OrderDetail = lazy(() => import('./pages/seller/OrderDetail'))
const Conversations = lazy(() => import('./pages/seller/Conversations'))
const ConversationDetail = lazy(() => import('./pages/seller/Conversations').then((m) => ({ default: m.ConversationDetail })))
const Products = lazy(() => import('./pages/seller/Products'))
const Knowledge = lazy(() => import('./pages/seller/Knowledge'))
const Account = lazy(() => import('./pages/seller/Account'))
const Team = lazy(() => import('./pages/seller/Team'))
const HomeSectionsAdmin = lazy(() => import('./pages/seller/HomeSectionsAdmin'))
const RoleDashboardRouter = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.RoleDashboardRouter })))
const CustomerDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.CustomerDashboard })))
const SupportDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.SupportDashboard })))
const GodDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.GodDashboard })))
const StoreSupportDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.StoreSupportDashboard })))
const PendingDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.PendingDashboard })))
const RejectedDashboard = lazy(() => import('./pages/RoleDashboards').then((module) => ({ default: module.RejectedDashboard })))

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
                  <Route path="about" element={<About />} />
                  <Route path="stores" element={<StoreDirectory />} />
                  <Route path="login" element={<AuthPage initial="login" />} />
                  <Route path="register" element={<AuthPage initial="register" />} />
                  <Route path="track" element={<Track />} />
                  <Route path="payment-result" element={<PaymentResult />} />
                  <Route path="api-docs" element={<ApiDocs />} />
                  <Route path="*" element={<NotFound />} />
                </Route>

                <Route path="workspace" element={<RequireAuth><RoleDashboardRouter /></RequireAuth>} />
                <Route path="workspace/customer" element={<RequireAuth><RequireRoles roles={['customer']}><Navigate to="/seller/customer" replace /></RequireRoles></RequireAuth>} />
                <Route path="workspace/support" element={<RequireAuth><RequireRoles roles={['support']}><Navigate to="/seller/support" replace /></RequireRoles></RequireAuth>} />
                <Route path="workspace/god" element={<RequireAuth><RequireRoles roles={['god']}><Navigate to="/seller/platform" replace /></RequireRoles></RequireAuth>} />
                <Route path="workspace/pending" element={<RequireAuth><PendingDashboard /></RequireAuth>} />
                <Route path="workspace/rejected" element={<RequireAuth><RejectedDashboard /></RequireAuth>} />

                <Route path="store/:id" element={<StoreShell />}>
                  <Route index element={<StoreHome />} />
                  <Route path="product/:productId" element={<ProductPage />} />
                </Route>

                <Route path="seller" element={<RequireAuth><RequireRoles roles={['store_owner', 'store_admin', 'customer', 'support', 'god']}><SellerLayout /></RequireRoles></RequireAuth>}>
                  <Route index element={<RequireStorePermission permission="store.read"><Overview /></RequireStorePermission>} />
                  <Route path="orders" element={<RequireStorePermission permission="order.read"><Orders /></RequireStorePermission>} />
                  <Route path="order/:orderId" element={<RequireStorePermission permission="order.read"><OrderDetail /></RequireStorePermission>} />
                  <Route path="conversations" element={<RequireStorePermission permission="conversation.read"><Conversations /></RequireStorePermission>} />
                  <Route path="conversation/:conversationId" element={<RequireStorePermission permission="conversation.read"><ConversationDetail /></RequireStorePermission>} />
                  <Route path="products" element={<RequireStorePermission permission="product.read"><Products /></RequireStorePermission>} />
                  <Route path="knowledge" element={<RequireStorePermission permission="knowledge.read"><Knowledge /></RequireStorePermission>} />
                  <Route path="team" element={<RequireStorePermission permission="member.read"><Team /></RequireStorePermission>} />
                  <Route path="contact-support" element={<RequireStorePermission permission="support.contact"><StoreSupportDashboard /></RequireStorePermission>} />
                  <Route path="account" element={<RequireRoles roles={['store_owner', 'store_admin', 'support', 'god']}><Account /></RequireRoles>} />
                  <Route path="support" element={<RequireRoles roles={['support', 'god']}><SupportDashboard /></RequireRoles>} />
                  <Route path="customer" element={<RequireRoles roles={['customer']}><CustomerDashboard /></RequireRoles>} />
                  <Route path="platform" element={<RequireRoles roles={['god']}><GodDashboard /></RequireRoles>} />
                  <Route path="platform/home-sections" element={<RequireRoles roles={['god']}><HomeSectionsAdmin /></RequireRoles>} />
                </Route>
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </AuthProvider>
      </ToastProvider>
    </I18nProvider>
  )
}
