import { useState } from 'react'
import { Async, Badge, Button, ConfirmButton, Empty, Field, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { useSeller } from './SellerContext'
import { NeedStore, PageHead } from './SellerLayout'

const MEMBER_ROLES = ['store_admin', 'store_manager', 'store_viewer']

export default function Team() {
  const { t, err } = useI18n()
  const toast = useToast()
  const { store } = useSeller()
  const permissions = new Set(store?.permissions || [])
  const canInvite = permissions.has('member.invite')
  const canApprove = permissions.has('member.approve')
  const canUpdate = permissions.has('member.update')
  const canRemove = permissions.has('member.remove')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('store_manager')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const members = useAsync(() => store ? api.seller.members(store.id) : null, [store?.id])
  useSeo({ title: `${t('dash.team')} | NAVA` })
  if (!store) return <NeedStore />

  const run = async (membership, payload, success) => {
    setBusy(true)
    try {
      await api.seller.updateMember(store.id, membership.id, payload)
      await members.reload()
      toast(success)
    } catch (cause) {
      toast(err(cause), 'danger')
    } finally {
      setBusy(false)
    }
  }

  const add = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.seller.addMember(store.id, { email: email.trim(), role })
      setEmail('')
      await members.reload()
      toast(t('dash.memberAdded'))
    } catch (cause) {
      setError(err(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHead title={t('dash.team')} />
      {canInvite && <section className="card stack">
        <h2 className="h3">{t('dash.addMember')}</h2>
        <form className="row" onSubmit={add}>
          <Field label={t('dash.email')}><input type="email" required maxLength={255} value={email} onChange={(event) => setEmail(event.target.value)} /></Field>
          <Field label={t('dash.role')}><select value={role} onChange={(event) => setRole(event.target.value)}>{MEMBER_ROLES.map((value) => <option key={value} value={value}>{t(`role.${value}`)}</option>)}</select></Field>
          <Button type="submit" variant="primary" busy={busy}>{t('dash.addMember')}</Button>
        </form>
        <p className="muted">{t('dash.memberExistingAccount')}</p>
        {error && <p className="notice notice-danger" role="alert">{error}</p>}
      </section>}
      <Async state={members}>{(items) => !items.length ? <Empty title={t('dash.noMembers')} /> : (
        <section className="card stack">
          <h2 className="h3">{t('dash.members')}</h2>
          <ul className="plain-list">{items.map((member) => <li key={member.id}>
            <span><strong>{member.name || member.email}</strong><br /><span dir="ltr">{member.email}</span></span>
            <span className="row">
              <Badge>{t(`dash.memberStatus.${member.status}`)}</Badge>
              {member.status === 'pending' && canApprove && <>
                <Button size="sm" busy={busy} onClick={() => run(member, { status: 'approved' }, t('dash.approve'))}>{t('dash.approve')}</Button>
                <Button size="sm" variant="danger" busy={busy} onClick={() => run(member, { status: 'rejected' }, t('dash.reject'))}>{t('dash.reject')}</Button>
              </>}
              {member.status === 'approved' && <>
                {canUpdate && <Field label={t('dash.role')}><select value={member.role} disabled={busy} onChange={(event) => run(member, { role: event.target.value }, t('saved'))}>{MEMBER_ROLES.map((value) => <option key={value} value={value}>{t(`role.${value}`)}</option>)}</select></Field>}
                {canRemove && <>
                  <ConfirmButton busy={busy} variant="danger" onConfirm={() => run(member, { status: 'suspended' }, t('dash.memberSuspended'))}>{t('dash.suspend')}</ConfirmButton>
                  <ConfirmButton busy={busy} variant="danger" onConfirm={() => run(member, { status: 'revoked' }, t('dash.memberRemoved'))}>{t('dash.removeMember')}</ConfirmButton>
                </>}
              </>}
              {['suspended', 'revoked'].includes(member.status) && canApprove && <Button size="sm" busy={busy} onClick={() => run(member, { status: 'approved' }, t('dash.memberReactivated'))}>{t('dash.reactivate')}</Button>}
            </span>
          </li>)}</ul>
        </section>
      )}</Async>
    </>
  )
}