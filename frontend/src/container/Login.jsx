import React from 'react'
import { connect } from 'react-redux'
import { withRouter, Redirect } from 'react-router'
import { translate } from 'react-i18next'
import i18n from '../i18n.js'
import * as Cookies from 'js-cookie'
import Card from '../component/common/Card/Card.jsx'
import CardHeader from '../component/common/Card/CardHeader.jsx'
import CardBody from '../component/common/Card/CardBody.jsx'
import InputGroupText from '../component/common/Input/InputGroupText.jsx'
import Button from '../component/common/Input/Button.jsx'
import FooterLogin from '../component/Login/FooterLogin.jsx'
import {
  newFlashMessage,
  setUserConnected,
  setWorkspaceList,
  setContentTypeList,
  setAppList,
  setConfig,
  resetBreadcrumbs,
  setUserLang
} from '../action-creator.sync.js'
import {
  getAppList,
  getConfig,
  getContentTypeList,
  getMyselfWorkspaceList,
  postUserLogin,
  putUserLang
} from '../action-creator.async.js'
import {
  PAGE,
  COOKIE_FRONTEND
} from '../helper.js'

const qs = require('query-string')

class Login extends React.Component {
  constructor (props) {
    super(props)
    this.state = {
      inputLogin: {
        value: '',
        isInvalid: false
      },
      inputPassword: {
        value: '',
        isInvalid: false
      },
      inputRememberMe: false
    }
  }

  async componentDidMount () {
    const { props } = this

    props.dispatch(resetBreadcrumbs())

    const defaultLangCookie = Cookies.get(COOKIE_FRONTEND.DEFAULT_LANGUAGE)

    if (defaultLangCookie && defaultLangCookie !== 'null') {
      i18n.changeLanguage(defaultLangCookie)
      props.dispatch(setUserLang(defaultLangCookie))
    }

    const query = qs.parse(props.location.search)
    if (query.dc && query.dc === '1') {
      props.dispatch(newFlashMessage(props.t('You have been disconnected, please login again', 'warning')))
      props.history.push(props.location.pathname)
      return
    }

    await this.loadConfig()
  }

  handleChangeLogin = e => this.setState({inputLogin: {...this.state.inputLogin, value: e.target.value}})
  handleChangePassword = e => this.setState({inputPassword: {...this.state.inputPassword, value: e.target.value}})
  handleChangeRememberMe = e => {
    e.preventDefault()
    e.stopPropagation()
    this.setState(prev => ({inputRememberMe: !prev.inputRememberMe}))
  }

  handleInputKeyDown = e => e.key === 'Enter' && this.handleClickSubmit()

  handleClickSubmit = async () => {
    const { props, state } = this

    if (state.inputLogin.value === '' || state.inputPassword.value === '') {
      props.dispatch(newFlashMessage(props.t('Please enter a login and a password'), 'warning'))
      return
    }

    const fetchPostUserLogin = await props.dispatch(postUserLogin(state.inputLogin.value, state.inputPassword.value, state.inputRememberMe))

    switch (fetchPostUserLogin.status) {
      case 200:
        const loggedUser = {
          ...fetchPostUserLogin.json,
          logged: true
        }

        if (fetchPostUserLogin.json.lang === null) this.setDefaultUserLang(fetchPostUserLogin.json)

        Cookies.set(COOKIE_FRONTEND.LAST_CONNECTION, '1', {expires: COOKIE_FRONTEND.DEFAULT_EXPIRE_TIME})
        props.dispatch(setUserConnected(loggedUser))

        Cookies.set(COOKIE_FRONTEND.DEFAULT_LANGUAGE, fetchPostUserLogin.json.lang, {expires: COOKIE_FRONTEND.DEFAULT_EXPIRE_TIME})
        i18n.changeLanguage(loggedUser.lang)

        this.loadAppList()
        this.loadContentTypeList()
        this.loadWorkspaceList()

        if (props.system.redirectLogin !== '') {
          props.history.push(props.system.redirectLogin)
          return
        }

        props.history.push(PAGE.HOME)
        break
      case 400:
        switch (fetchPostUserLogin.json.code) {
          case 2001: props.dispatch(newFlashMessage(props.t('Not a valid email'), 'warning')); break
          default: props.dispatch(newFlashMessage(props.t('An error has happened'), 'warning')); break
        }
        break
      case 403: props.dispatch(newFlashMessage(props.t('Email or password invalid'), 'warning')); break
      default: props.dispatch(newFlashMessage(props.t('An error has happened'), 'warning')); break
    }
  }

  loadConfig = async () => {
    const { props } = this

    const fetchGetConfig = await props.dispatch(getConfig())
    if (fetchGetConfig.status === 200) props.dispatch(setConfig(fetchGetConfig.json))
  }

  loadAppList = async () => {
    const { props } = this

    const fetchGetAppList = await props.dispatch(getAppList())
    if (fetchGetAppList.status === 200) props.dispatch(setAppList(fetchGetAppList.json))
  }

  loadContentTypeList = async () => {
    const { props } = this

    const fetchGetContentTypeList = await props.dispatch(getContentTypeList())
    if (fetchGetContentTypeList.status === 200) props.dispatch(setContentTypeList(fetchGetContentTypeList.json))
  }

  loadWorkspaceList = async () => {
    const { props } = this
    const fetchGetWorkspaceList = await props.dispatch(getMyselfWorkspaceList())
    if (fetchGetWorkspaceList.status === 200) props.dispatch(setWorkspaceList(fetchGetWorkspaceList.json))
  }

  setDefaultUserLang = async loggedUser => {
    const { props } = this
    const fetchPutUserLang = await props.dispatch(putUserLang(loggedUser, props.user.lang))
    switch (fetchPutUserLang.status) {
      case 200: break
      default: props.dispatch(newFlashMessage(props.t('Error while saving your language')))
    }
  }

  handleClickForgotPassword = () => {
    const { props } = this
    props.history.push(
      props.system.config.email_notification_activated
        ? PAGE.FORGOT_PASSWORD
        : PAGE.FORGOT_PASSWORD_NO_EMAIL_NOTIF
    )
  }

  render () {
    const { props, state } = this
    if (props.user.logged) return <Redirect to={{pathname: '/ui'}} />

    return (
      <section className='loginpage primaryColorBg'>
        <Card customClass='loginpage__card'>
          <CardHeader customClass='loginpage__card__header primaryColorBgLighten'>
            {props.t('Connection')}
          </CardHeader>

          <CardBody formClass='loginpage__card__form'>
            <form>
              <InputGroupText
                parentClassName='loginpage__card__form__groupemail'
                customClass='mb-3 mt-4'
                icon='fa-envelope-open-o'
                type='email'
                placeHolder={props.t('Email Address')}
                invalidMsg={props.t('Invalid email')}
                isInvalid={state.inputLogin.isInvalid}
                value={state.inputLogin.value}
                onChange={this.handleChangeLogin}
                onKeyDown={this.handleInputKeyDown}
                maxLength={512}
              />

              <InputGroupText
                parentClassName='loginpage__card__form__groupepw'
                customClass=''
                icon='fa-lock'
                type='password'
                placeHolder={props.t('Password')}
                invalidMsg={props.t('Invalid password')}
                isInvalid={state.inputPassword.isInvalid}
                value={state.inputPassword.value}
                onChange={this.handleChangePassword}
                onKeyDown={this.handleInputKeyDown}
                maxLength={512}
              />

              <div className='row mt-4 mb-4'>
                <div className='col-12 col-sm-6'>
                  <div
                    className='loginpage__card__form__pwforgot'
                    onClick={this.handleClickForgotPassword}
                  >
                    {props.t('Forgotten password ?')}
                  </div>
                </div>

                <div className='col-12 col-sm-6 d-flex align-items-end'>
                  <Button
                    htmlType='button'
                    bootstrapType='primary'
                    customClass='btnSubmit loginpage__card__form__btnsubmit ml-auto'
                    label={props.t('Connection')}
                    onClick={this.handleClickSubmit}
                  />
                </div>
              </div>
            </form>
          </CardBody>
        </Card>

        <FooterLogin />
      </section>
    )
  }
}

const mapStateToProps = ({ user, system, breadcrumbs }) => ({ user, system, breadcrumbs })
export default withRouter(connect(mapStateToProps)(translate()(Login)))
